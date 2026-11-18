from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import domain as d
from . import models as m
from . import runtime
from . import format_plugins
from . import itam_bridge

app = FastAPI(title='Deep Agent Platform')
itam_bridge.install(app)
d.init()
runtime.initialize()
app.include_router(runtime.router)
app.include_router(format_plugins.router)
class ArtifactHost:
    def session(self,session_id):return runtime.find(session_id)
    def service(self,session_id,feature):
        if feature not in [m['id'] for m in format_plugins.enabled()]:raise HTTPException(404,'Feature is uninstalled or disabled')
        value=runtime.runtime(session_id).ensure_artifact_services().get(feature)
        if value is None:raise HTTPException(503,'Feature dependencies unavailable')
        return value
    def emit(self,session_id,event):runtime.runtime(session_id).event(event)
artifact_host=ArtifactHost()
for feature in format_plugins.enabled():
    try:
        plugin=format_plugins.load_plugin(feature['id'])
        if hasattr(plugin,'create_router'):app.include_router(plugin.create_router(artifact_host))
    except (ImportError,LookupError):pass

@app.get('/api/status')
def status():
    return {'model_configured': any(p['configured'] for p in m.options(itam_bridge.owner())['profiles']), 'mode': 'itam-multi-user' if itam_bridge.is_enabled() else 'single-user', 'core': 'platform_app.agent_core'}


class ModelConfig(BaseModel):
    llm: dict
    revision: int


@app.get('/api/models')
def models():
    return m.public()


@app.put('/api/models')
def update_models(value: ModelConfig):
    try:
        return m.save(value.llm, value.revision)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    except Exception:
        raise HTTPException(422, '模型配置无效：请检查来源、默认模型、API 协议和 llm 参数。')


@app.get('/api/models/options')
def model_options():
    return m.options(itam_bridge.owner())


def personal_owner():
    owner = itam_bridge.owner()
    if owner is None:
        raise HTTPException(404, '个人模型配置仅在 ITAM 多用户模式下可用')
    return owner


@app.get('/api/models/personal')
def personal_models():
    return m.public_personal(personal_owner())


@app.put('/api/models/personal')
def update_personal_models(value: ModelConfig):
    owner = personal_owner()
    try:
        return m.save_personal(owner, value.llm, value.revision)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, f'个人模型配置无效：{exc}')


@app.get('/api/settings')
def settings():
    return d.effective_config()


@app.get('/api/tool-catalog')
def tool_catalog():
    return []


@app.put('/api/settings')
def update_settings(value: dict):
    with d.LOCK:
        previous = d.get('settings', 'global')
        if value.get('revision') != previous['revision']:
            raise HTTPException(409, '配置已更新，请刷新后重试')
        edits = {k: v for k, v in value.items() if k in ('system_prompt', 'rules', 'skills', 'tools', 'core_tools', 'mcp', 'skill_bindings')}
        if isinstance(edits.get('tools'), list):
            edits['tools'] = [tool for tool in edits['tools'] if not isinstance(tool, dict) or tool.get('name') not in d.REMOVED_TOOLS]
        value = {**previous, 'tools': [], **edits}
        try:
            d.validate_config(value)
        except Exception as exc:
            raise HTTPException(422, str(exc))
        value['revision'] += 1
        d.put('settings', value)
        return d.effective_config()


def capabilities_editable():
    return not itam_bridge.is_enabled() or itam_bridge.ROLE.get() == 'admin'


def platform_capabilities():
    value = d.effective_config()
    core = value.get('core_tools', {})
    return {
        'revision': value['revision'],
        'editable': capabilities_editable(),
        'core_tools': [{'name': name, 'enabled': core.get(name, True)} for name in d.CORE_TOOLS],
        'tools': [],
        'skills': [{k: skill.get(k) for k in ('id', 'name', 'description', 'source', 'feature_id', 'enabled')} | {'available': skill.get('available', True)}
                   for skill in value['native_skills']],
    }


class CapabilityMounts(BaseModel):
    model_config = {'extra': 'forbid'}
    revision: int
    core_tools: dict[str, bool] = {}
    tools: dict[str, bool] = {}
    skill_bindings: dict[str, bool] = {}


@app.get('/api/platform/capabilities')
def get_platform_capabilities():
    return platform_capabilities()


@app.put('/api/platform/capabilities')
def update_platform_capabilities(value: CapabilityMounts):
    """Mount or unmount tools and skills for new sessions; only the mount switches are editable."""
    if not capabilities_editable():
        raise HTTPException(403, 'Admin permission required')
    with d.LOCK:
        previous = d.get('settings', 'global')
        if value.revision != previous['revision']:
            raise HTTPException(409, '配置已更新，请刷新后重试')
        if value.tools:
            raise HTTPException(422, '工具未注册，请刷新后重试')
        unavailable = {s['id'] for s in d.native_skills() if s.get('available') is False}
        if any(enabled and key in unavailable for key, enabled in value.skill_bindings.items()):
            raise HTTPException(422, '扩展功能已停用，无法挂载其 Skill')
        updated = {**previous,
                   'core_tools': {**previous.get('core_tools', {}), **value.core_tools},
                   'skill_bindings': {**previous.get('skill_bindings', {}), **value.skill_bindings},
                   'tools': []}
        try:
            d.validate_config(updated)
        except Exception as exc:
            raise HTTPException(422, str(exc))
        updated['revision'] += 1
        d.put('settings', updated)
    return platform_capabilities()
