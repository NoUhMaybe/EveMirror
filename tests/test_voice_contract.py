import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.server.speech.delivery import Delivery
from packages.audio import SpeechAudio, SpeechError
from packages.protocol import PlaybackStatus, PlaybackStatusPayload
from scripts.export_application import voice_schema
from tests.test_edge_integration import until


def test_voice_snapshot_schema_matches_models():
    assert json.loads(Path("packages/application/voice.schema.json").read_text()) == voice_schema()


def test_edge_imports_with_server_and_heavy_speech_modules_explicitly_blocked():
    code = """
import importlib.abc
import sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        blocked = {'fastapi','openai','anthropic','mcp','torch','piper','faster_whisper',
                   'openwakeword','onnxruntime','numpy','soxr','sounddevice'}
        if name.split('.')[0] in blocked or name.startswith('apps.server'):
            raise ImportError('Unexpected eager import: '+name)
sys.meta_path.insert(0, Block())
import apps.edge.runtime
print('Edge import remains independent of server and optional audio/model dependencies.')
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr


async def test_playback_flow_control_waits_for_each_ack_and_times_out_without_claiming_completion():
    sent = []

    class Connection:
        state = SimpleNamespace(device_id="mirror-1")

        async def send(self, event):
            sent.append(event)

    connection = Connection()
    delivery = Delivery(0.05)
    session = uuid4()
    task = asyncio.create_task(
        delivery.play(connection, SpeechAudio(b"\x01\x00" * 9000, 16000), session)
    )
    await until(lambda: len(sent) == 1)
    begin = sent[0]
    await asyncio.sleep(0.01)
    assert len(sent) == 1  # no audio allocated/sent ahead of acceptance
    foreign = PlaybackStatus(
        device_id="mirror-1",
        session_id=uuid4(),
        request_id=begin.request_id,
        payload=PlaybackStatusPayload(status="accepted"),
    )
    assert not delivery.receive(connection, foreign)
    delivery.receive(connection, foreign.model_copy(update={"session_id": session}))
    await until(lambda: len(sent) == 2)
    assert sent[-1].type == "playback.chunk"
    await asyncio.sleep(0.01)
    assert len(sent) == 2  # second frame waits for the first frame's byte receipt
    delivery.receive(
        connection,
        PlaybackStatus(
            device_id="mirror-1",
            session_id=session,
            request_id=begin.request_id,
            payload=PlaybackStatusPayload(status="buffered", next_sequence=1),
        ),
    )
    await until(lambda: len(sent) == 3)
    assert sent[-1].payload.sequence == 1
    with pytest.raises(SpeechError, match="playback_timeout"):
        await task
    assert sent[-1].type == "playback.cancel" and not delivery.pending
