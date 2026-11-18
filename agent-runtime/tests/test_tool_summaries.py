import asyncio
from types import SimpleNamespace

from platform_app.agent_core.config import SandboxConfig
from platform_app.agent_core.middleware.workspace_filesystem import WorkspaceFilesystemMiddleware
from platform_app.agent_core.middleware.write_operation import WriteOperationMiddleware
from platform_app.agent_core.sandbox import BubblewrapBackend, WorkspaceCompositeBackend


def test_file_tool_summaries_with_real_workspace(tmp_path):
    executor = BubblewrapBackend(SandboxConfig(workspace=tmp_path, mount_skills=False), executable="bwrap")
    backend = WorkspaceCompositeBackend(executor, skills_dir=None)
    tools = {tool.name: tool for tool in WorkspaceFilesystemMiddleware(backend=backend).tools}
    middleware = WriteOperationMiddleware(backend)
    runtime = SimpleNamespace(tool_call_id="call")

    def request(name, args):
        return SimpleNamespace(tool_call={"type": "tool_call", "name": name, "args": args, "id": "call"})

    def invoke(name, **args):
        return middleware.wrap_tool_call(request(name, args), lambda req: tools[name].func(runtime=runtime, **req.tool_call["args"]))

    async def ainvoke(name, **args):
        return await middleware.awrap_tool_call(
            request(name, args), lambda req: tools[name].coroutine(runtime=runtime, **req.tool_call["args"])
        )

    folder = backend.workspace_root + "/files"
    (tmp_path / "files").mkdir()
    assert invoke("ls", path=folder).artifact["file_summary"] == {"entries": [], "total": 0}
    target = folder + "/report.md"
    create = invoke("write_file", file_path=target, content="first\nold\nold\n")
    assert create.artifact == {"operation": "create", "file_summary": {"removed": 0, "added": 3}}
    assert "first" in invoke("read_file", file_path=target).content

    edit = asyncio.run(ainvoke("edit_file", file_path=target, old_string="old", new_string="new", replace_all=True))
    assert edit.artifact["file_summary"] == {"removed": 2, "added": 2}
    ok = invoke("edit_file", file_path=target, old_string="new\n", new_string="", replace_all=True)
    assert ok.artifact["file_summary"] == {"removed": 2, "added": 0}
    failed = invoke("edit_file", file_path=target, old_string="missing", new_string="unused")
    assert failed.status == "error" and failed.artifact is None
    overwrite = invoke("write_file", file_path=target, content="replacement\n")
    assert overwrite.artifact == {"operation": "overwrite", "file_summary": {"removed": 1, "added": 1}}
    unchanged = invoke("write_file", file_path=target, content="replacement\n")
    assert unchanged.artifact["file_summary"] == {"removed": 0, "added": 0}
    for name in ("a.txt", "b's.txt", "c.txt", "d.txt"):
        (tmp_path / "files" / name).touch()
    listed = asyncio.run(ainvoke("ls", path=folder))
    assert listed.artifact["file_summary"] == {"entries": [f"{folder}/{name}" for name in ("a.txt", "b's.txt", "c.txt")], "total": 5}
    assert "d.txt" in listed.content

    binary = tmp_path / "files" / "binary.dat"
    binary.write_bytes(b"\x00\xff")
    assert invoke("write_file", file_path=folder + "/binary.dat", content="text").artifact["file_summary"] == {}
