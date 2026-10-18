import base64
from uuid import uuid4

import pytest

from apps.server.audio import AudioAssembler, AudioError
from packages.protocol import (
    AudioBegin,
    AudioBeginPayload,
    AudioChunk,
    AudioChunkPayload,
    AudioEnd,
    AudioEndPayload,
)


def utterance(pcm=b"\x00\x01" * 200):
    identity = {"device_id": "mirror-1", "session_id": uuid4(), "request_id": uuid4()}
    return (
        AudioBegin(**identity, payload=AudioBeginPayload(total_bytes=len(pcm))),
        AudioChunk(
            **identity,
            payload=AudioChunkPayload(
                sequence=0,
                data=base64.b64encode(pcm).decode(),
            ),
        ),
        AudioEnd(**identity, payload=AudioEndPayload(chunks=1)),
    )


def test_audio_exact_bytes_without_disk():
    begin, chunk, end = utterance()
    assembler = AudioAssembler()
    assembler.start(begin)
    assembler.append(chunk)
    result = assembler.finish(end)
    assert result.pcm == b"\x00\x01" * 200
    assert assembler.begin is None and not assembler.buffer
    assert "pcm=" not in repr(result)


@pytest.mark.parametrize(
    "patch",
    [
        {"sequence": 1},
        {"data": "!!!!"},
        {"data": "AQ=="},
        {"data": base64.b64encode(b"\0" * 16002).decode()},
    ],
)
def test_audio_rejects_corruption_and_reordering(patch):
    begin, chunk, _ = utterance()
    assembler = AudioAssembler()
    assembler.start(begin)
    chunk = chunk.model_copy(update={"payload": chunk.payload.model_copy(update=patch)})
    with pytest.raises(AudioError):
        assembler.append(chunk)


def test_incomplete_upload_and_identity():
    begin, chunk, end = utterance()
    assembler = AudioAssembler()
    assembler.start(begin)
    with pytest.raises(AudioError, match="Incomplete"):
        assembler.finish(end)
    with pytest.raises(AudioError, match="matching"):
        assembler.append(chunk.model_copy(update={"session_id": uuid4()}))


def test_expiry_and_limits(monkeypatch):
    now = [0.0]
    monkeypatch.setattr("apps.server.audio.time.monotonic", lambda: now[0])
    begin, chunk, _ = utterance()
    assembler = AudioAssembler(timeout=1)
    assembler.start(begin)
    assembler.append(chunk)
    now[0] = 2
    assert assembler.expire()
    assert assembler.begin is None and not assembler.buffer
    with pytest.raises(ValueError):
        AudioBeginPayload(total_bytes=960_002)
    with pytest.raises(ValueError):
        AudioBeginPayload(total_bytes=3)
