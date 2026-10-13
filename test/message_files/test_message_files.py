"""Regression: attaching files to a message whose stored `files` is null.

The image tools call `Chats.add_message_files_by_id_and_message_id` after generating an image.
When the message held `files: null`, `.get('files', [])` returned None and `None + list` raised,
so the image was generated but never attached.

chats.py is loaded by file path with its `open_webui` imports stubbed, so only sqlalchemy and
pydantic are needed:
    uv run --no-project --with pytest --with 'sqlalchemy[asyncio]' --with pydantic \
        python -m pytest test/message_files -q
"""

import asyncio
import importlib.util
import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import JSON
from sqlalchemy.orm import declarative_base

PATH = Path(__file__).resolve().parents[2] / 'backend' / 'open_webui' / 'models' / 'chats.py'


class Recorder:
    def __init__(self):
        self.calls = []

    async def upsert_message(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def stub(name, **attributes):
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    return module


def load_chats(recorder):
    anything = type('Anything', (), {})
    stubs = {
        'open_webui': stub('open_webui'),
        'open_webui.env': stub('open_webui.env', ENABLE_ADMIN_CHAT_ACCESS=True),
        'open_webui.internal': stub('open_webui.internal'),
        'open_webui.internal.db': stub(
            'open_webui.internal.db',
            Base=declarative_base(),
            JSONField=JSON,
            get_async_db=None,
            get_async_db_context=None,
        ),
        'open_webui.models': stub('open_webui.models'),
        'open_webui.models.access_grants': stub('open_webui.models.access_grants', AccessGrants=anything),
        'open_webui.models.automations': stub('open_webui.models.automations', AutomationRun=anything),
        'open_webui.models.chat_messages': stub(
            'open_webui.models.chat_messages', ChatMessage=anything, ChatMessages=recorder
        ),
        'open_webui.models.folders': stub('open_webui.models.folders', Folders=anything),
        'open_webui.models.tags': stub('open_webui.models.tags', Tag=anything, TagModel=anything, Tags=anything),
        'open_webui.utils': stub('open_webui.utils'),
        'open_webui.utils.misc': stub(
            'open_webui.utils.misc',
            get_output_text=lambda output: '',
            sanitize_data_for_db=lambda data: data,
            sanitize_text_for_db=lambda text: text,
        ),
    }
    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location('chats_under_test', PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    module.flag_modified = lambda instance, key: None
    return module


def table_with_chat(module, chat):
    chat_item = types.SimpleNamespace(chat=chat, user_id='user-1', updated_at=0)
    table = module.ChatTable()

    @asynccontextmanager
    async def transaction(chat_id):
        yield None, chat_item

    table._chat_transaction = transaction
    return table, chat_item


def run_attach(stored_message):
    recorder = Recorder()
    module = load_chats(recorder)
    chat = {'history': {'messages': {'message-1': stored_message}}}
    table, chat_item = table_with_chat(module, chat)
    image = {'type': 'image', 'url': '/api/v1/files/abc/content'}
    result = asyncio.run(table.add_message_files_by_id_and_message_id('chat-1', 'message-1', [image]))
    return result, chat_item, recorder, image


def test_null_files_are_replaced_by_the_new_files():
    result, chat_item, recorder, image = run_attach({'role': 'assistant', 'content': '', 'files': None})
    assert result == [image]
    assert chat_item.chat['history']['messages']['message-1']['files'] == [image]
    assert len(recorder.calls) == 1


def test_missing_files_key_still_works():
    result, chat_item, _, image = run_attach({'role': 'assistant', 'content': ''})
    assert result == [image]


def test_existing_files_are_kept():
    existing = {'type': 'image', 'url': '/api/v1/files/old/content'}
    result, chat_item, _, image = run_attach({'role': 'assistant', 'content': '', 'files': [existing]})
    assert result == [existing, image]
