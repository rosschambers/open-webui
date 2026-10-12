"""Named sub-agents (fork patch, rosschambers/open-webui branch `agents`).

A Workspace Model with meta.capabilities.subagent = true is a named agent. delegate_task
gets an optional `agent` argument; the child then runs on that model with only that model's
tools, prompt and skills, and the parent resumes on its own model.

Module level imports nothing from open_webui so the pure helpers are unit-testable.
"""

from __future__ import annotations

import copy
from typing import Any

AGENT_CAPABILITY = 'subagent'


def _meta(model: dict) -> dict:
    return (model.get('info') or {}).get('meta') or {}


def is_agent(model: dict) -> bool:
    if model.get('arena'):
        return False
    return bool((_meta(model).get('capabilities') or {}).get(AGENT_CAPABILITY))


def agent_entries(models: list[dict]) -> list[dict]:
    entries = []
    for model in models:
        if not is_agent(model) or (model.get('info') or {}).get('is_active') is False:
            continue
        entries.append(
            {
                'id': model['id'],
                'name': model.get('name') or model['id'],
                'description': ' '.join(str(_meta(model).get('description') or '').split()),
            }
        )
    return sorted(entries, key=lambda entry: entry['name'].lower())


def inject_agent_parameter(spec: dict, agents: list[dict]) -> None:
    lines = []
    for agent in agents:
        line = f'{agent["id"]} — {agent["name"]}'
        if agent['description']:
            line += f': {agent["description"]}'
        lines.append(line)
    spec.setdefault('parameters', {}).setdefault('properties', {})['agent'] = {
        'type': 'string',
        'enum': [agent['id'] for agent in agents],
        'description': (
            'Optional named agent to run the task. The agent uses its own model, instructions and tools and '
            'cannot see this conversation, so the task must be self-contained. Omit to use the current model.\n'
            'Available agents:\n' + '\n'.join(f'- {line}' for line in lines)
        ),
    }
    spec['description'] = (
        'Delegate focused work to a parallel sub-agent. By default it uses the current model and tools; '
        'set `agent` to hand the task to a named agent with its own model, instructions and tools.'
    )


def remove_agent_parameter(spec: dict) -> None:
    (spec.get('parameters') or {}).get('properties', {}).pop('agent', None)


def resolve_agent(agents: list[dict], requested: str) -> dict | str:
    wanted = requested.strip()
    for agent in agents:
        if agent['id'] == wanted:
            return agent
    for agent in agents:
        if agent['name'].lower() == wanted.lower():
            return agent
    if not agents:
        return f"Error: unknown agent '{wanted}'. No agents are configured."
    return f"Error: unknown agent '{wanted}'. Available agents: {', '.join(agent['id'] for agent in agents)}"


def build_child_run(parent_run: dict, agent: dict, defaults: dict) -> dict[str, Any]:
    parent_context = parent_run.get('chat_context') or {}
    return {
        'model_id': agent['id'],
        'session_id': parent_run.get('session_id'),
        'tool_ids': list(defaults.get('tool_ids') or []),
        'skill_ids': [],
        'chat_context': {
            'params': {},
            'messages': [],
            'chat_variables': copy.deepcopy(parent_context.get('chat_variables')),
        },
        'tool_servers': [],
        'filter_ids': list(defaults.get('filter_ids') or []),
        'terminal_id': defaults.get('terminal_id') or None,
        'features': dict(defaults.get('features') or {}),
        'files': copy.deepcopy(parent_run.get('files') or []),
        'variables': copy.deepcopy(parent_run.get('variables') or {}),
        'direct': False,
        'folder_id': parent_run.get('folder_id'),
    }


async def list_agents(request: Any, user: Any) -> list[dict]:
    """Named agents the user may use, from the server's loaded model list."""
    from open_webui.utils.models import get_all_models, get_filtered_models

    models = list((getattr(request.app.state, 'MODELS', None) or {}).values())
    if not models:
        models = await get_all_models(request, user=user)
    accessible = await get_filtered_models([model for model in models if is_agent(model)], user)
    return agent_entries(accessible)
