import copy
import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / 'backend' / 'open_webui' / 'utils' / 'named_agents.py'
SPEC = importlib.util.spec_from_file_location('named_agents', PATH)
na = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(na)


def model(model_id, name, subagent=True, description='', is_active=True, arena=False):
    return {'id': model_id, 'name': name, 'arena': arena,
            'info': {'is_active': is_active, 'meta': {'description': description, 'capabilities': {'subagent': subagent}}}}


def test_is_agent():
    assert na.is_agent(model('a', 'A'))
    assert not na.is_agent(model('b', 'B', subagent=False))
    assert not na.is_agent(model('c', 'C', arena=True))
    assert not na.is_agent({'id': 'flash', 'name': 'flash'})


def test_agent_entries_sorted_and_filtered():
    entries = na.agent_entries([model('z', 'Zed', description='last'), model('a', 'alpha'),
                                model('off', 'Off', is_active=False), model('no', 'No', subagent=False)])
    assert entries == [{'id': 'a', 'name': 'alpha', 'description': ''}, {'id': 'z', 'name': 'Zed', 'description': 'last'}]


def test_inject_and_remove_agent_parameter():
    spec = {'description': 'Delegate.', 'parameters': {'type': 'object', 'properties': {'task': {'type': 'string'}}, 'required': ['task']}}
    na.inject_agent_parameter(spec, [{'id': 'murmur8', 'name': 'Murmur8', 'description': 'tasks and mail'}])
    agent = spec['parameters']['properties']['agent']
    assert agent['enum'] == ['murmur8']
    assert 'murmur8 — Murmur8: tasks and mail' in agent['description']
    assert spec['parameters']['required'] == ['task']
    na.remove_agent_parameter(spec)
    assert 'agent' not in spec['parameters']['properties']


def test_resolve_agent():
    agents = [{'id': 'home-agent', 'name': 'Home', 'description': ''}]
    assert na.resolve_agent(agents, 'home-agent')['id'] == 'home-agent'
    assert na.resolve_agent(agents, 'home')['id'] == 'home-agent'
    assert na.resolve_agent(agents, 'nope') == "Error: unknown agent 'nope'. Available agents: home-agent"
    assert na.resolve_agent([], 'x') == "Error: unknown agent 'x'. No agents are configured."


def test_build_child_run_uses_agent_and_does_not_mutate_parent():
    parent = {'model_id': 'flash', 'session_id': 's', 'tool_ids': ['ask_agent', 'server:mcp:n8n'], 'skill_ids': ['x'],
              'chat_context': {'params': {'system': 'parent prompt'}, 'messages': [{'role': 'system', 'content': 'p'}], 'chat_variables': {'v': 1}},
              'tool_servers': [{'url': 'u'}], 'filter_ids': ['f'], 'terminal_id': 'exocortex', 'features': {'web_search': True},
              'files': [{'id': 'f1'}], 'variables': {'a': 1}, 'direct': False, 'folder_id': 'fold'}
    before = copy.deepcopy(parent)
    child = na.build_child_run(parent, {'id': 'home', 'name': 'Home'}, {'tool_ids': ['server:mcp:home-assistant']})
    assert parent == before
    assert child['model_id'] == 'home'
    assert child['tool_ids'] == ['server:mcp:home-assistant']
    assert child['filter_ids'] == [] and child['terminal_id'] is None and child['features'] == {}
    assert child['skill_ids'] == [] and child['tool_servers'] == []
    assert child['chat_context'] == {'params': {}, 'messages': [], 'chat_variables': {'v': 1}}
    assert child['files'] == [{'id': 'f1'}] and child['session_id'] == 's' and child['folder_id'] == 'fold'
