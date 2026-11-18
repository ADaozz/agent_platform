"""Attach compact filesystem summaries to tool results."""
from __future__ import annotations

from ast import literal_eval
import asyncio
from difflib import SequenceMatcher
from typing import Any, Awaitable, Callable

from deepagents.backends.protocol import BackendProtocol, LsResult
from deepagents.backends.utils import (
    TOOL_RESULT_TOKEN_LIMIT,
    TRUNCATION_GUIDANCE,
    perform_string_replacement,
    validate_path,
)
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

from platform_app.agent_core.file_mutation import WriteOperation

_MAX_SNAPSHOT_BYTES = 256 * 1024
_MAX_DIFF_PAIRS = 1_000_000
_LIST_LIMIT = 3


def _operation(result: LsResult) -> WriteOperation | None:
    error = result.error or ""
    if error.endswith(": path_not_found"):
        return "create"
    if error.endswith(": not_a_directory"):
        return "overwrite"
    return None


def _text(contents: bytes | None) -> str | None:
    if contents is None or b"\0" in contents:
        return None
    try:
        return contents.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _line_diff(before: str, after: str) -> dict[str, int]:
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    start, old_end, new_end = 0, len(old), len(new)
    while start < min(old_end, new_end) and old[start] == new[start]:
        start += 1
    while min(old_end, new_end) > start and old[old_end - 1] == new[new_end - 1]:
        old_end -= 1
        new_end -= 1
    if (old_end - start) * (new_end - start) > _MAX_DIFF_PAIRS:
        return {}
    changes = SequenceMatcher(None, old[start:old_end], new[start:new_end], autojunk=False).get_opcodes()
    return {
        "removed": sum(end - begin for op, begin, end, _, _ in changes if op != "equal"),
        "added": sum(end - begin for op, _, _, begin, end in changes if op != "equal"),
    }


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _list_summary(content: Any) -> dict[str, Any]:
    if content == "No files found":
        return {"entries": [], "total": 0}
    if not isinstance(content, str) or len(content) > TOOL_RESULT_TOKEN_LIMIT * 4:
        return {}
    try:
        entries = literal_eval(content)
    except (SyntaxError, ValueError, RecursionError):
        return {}
    if not isinstance(entries, list) or not all(isinstance(entry, str) for entry in entries):
        return {}
    truncated = bool(entries and entries[-1] == TRUNCATION_GUIDANCE)
    if truncated:
        entries.pop()
    return {"entries": entries[:_LIST_LIMIT], "total": None if truncated else len(entries)}


class WriteOperationMiddleware(AgentMiddleware):
    """Classify writes and record presentation metadata separately from tool output."""

    def __init__(self, backend: BackendProtocol) -> None:
        super().__init__()
        self._backend = backend

    def _before(self, args: dict, name: str | None) -> tuple[str | None, WriteOperation | None, str | None]:
        path = args.get("file_path")
        if name not in ("write_file", "edit_file") or not isinstance(path, str):
            return None, None, None
        operation = None
        try:
            path = validate_path(path)
            if name == "write_file":
                operation = _operation(self._backend.ls(path))
            snapshot = getattr(self._backend, "file_mutation_snapshot", None)
            if snapshot is not None:
                before = "" if operation == "create" else _text(snapshot(path, _MAX_SNAPSHOT_BYTES))
                return path, operation, before
        except (ValueError, OSError, RuntimeError, NotImplementedError):
            pass
        return None, operation, None

    def _mutation_summary(self, name: str, args: dict, path: str | None, before: str | None) -> dict[str, int]:
        if path is None or before is None:
            return {}
        if name == "write_file":
            expected = args.get("content")
        else:
            old, new = args.get("old_string"), args.get("new_string")
            if not isinstance(old, str) or not old or not isinstance(new, str) or len(new) > _MAX_SNAPSHOT_BYTES:
                return {}
            original, old, new = _normalized(before), _normalized(old), _normalized(new)
            if len(original) + original.count(old) * (len(new) - len(old)) > _MAX_SNAPSHOT_BYTES:
                return {}
            edit = perform_string_replacement(original, old, new, args.get("replace_all", False))
            expected = edit[0] if isinstance(edit, tuple) else None
        if not isinstance(expected, str) or len(expected) > _MAX_SNAPSHOT_BYTES:
            return {}
        after = _text(self._backend.file_mutation_snapshot(path, _MAX_SNAPSHOT_BYTES))
        return _line_diff(before, after) if after is not None and after == expected else {}

    def _annotate(
        self, result: Any, name: str | None, args: dict,
        before: tuple[str | None, WriteOperation | None, str | None],
    ) -> Any:
        if not isinstance(result, ToolMessage) or result.status == "error":
            return result
        path, operation, previous = before
        artifact = dict(result.artifact) if isinstance(result.artifact, dict) else {}
        if name == "ls":
            artifact["file_summary"] = _list_summary(result.content)
        elif name in ("write_file", "edit_file"):
            if operation is not None:
                artifact["operation"] = operation
            try:
                artifact["file_summary"] = self._mutation_summary(name, args, path, previous)
            except (ValueError, OSError, RuntimeError, NotImplementedError):
                artifact["file_summary"] = {}
        else:
            return result
        return result.model_copy(update={"artifact": artifact})

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        call = request.tool_call
        name, args = call.get("name"), call.get("args") or {}
        before = self._before(args, name)
        return self._annotate(handler(request), name, args, before)

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
        call = request.tool_call
        name, args = call.get("name"), call.get("args") or {}
        if name not in ("write_file", "edit_file"):
            return self._annotate(await handler(request), name, args, (None, None, None))
        before = await asyncio.to_thread(self._before, args, name)
        result = await handler(request)
        return await asyncio.to_thread(self._annotate, result, name, args, before)
