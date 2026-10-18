import asyncio
from uuid import UUID, uuid4

from apps.config import VoiceGrant
from apps.edge.hardware import SimulatedHardware
from apps.edge.runtime import EdgeRuntime
from apps.server.tools.base import Principal
from tests.service_fixtures import FakeClock
from tests.test_edge_integration import live_server, until
from tests.test_voice_endtoend import edge_settings
from tests.voice_fixtures import STT, TTS, Detector, Microphone, Speaker


async def test_offline_alarm_reboot_lost_ack_reconciliation_server_restart_and_explicit_dismiss(
    settings, tmp_path
):
    clock = FakeClock()
    settings.speech.enabled = True
    settings.speech.alarm_poll_seconds = 0.05
    settings.voice_devices = {"mirror-1": VoiceGrant()}
    owner = Principal("operator", frozenset({"mirror-1"}), True)
    stt, tts, speaker = STT(), TTS(), Speaker()
    identities = []

    async with live_server(settings, service_clock=clock, speech_stt=stt, speech_tts=tts) as (
        app,
        port,
    ):
        runtime = EdgeRuntime(
            edge_settings(tmp_path, port),
            SimulatedHardware(),
            audio_source=Microphone(),
            detector=Detector(),
            speaker=speaker,
            voice_utc_clock=clock,
        )
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            await until(
                lambda: bool(app.state.voice.sync_pending.get("mirror-1", {}).get("stored"))
            )
            previous = app.state.voice.sync_pending["mirror-1"]["generation"]
            for _ in range(2):
                result, _ = await app.state.services.timers.mutate(
                    owner, "mirror-1", uuid4(), "create", duration_seconds=1
                )
                identities.append(result["data"]["timer"]["id"])
            await until(
                lambda: (
                    app.state.voice.sync_pending["mirror-1"]["generation"] != previous
                    and app.state.voice.sync_pending["mirror-1"]["stored"]
                )
            )
            runtime.settings.server_url = "ws://127.0.0.1:1"  # loopback refusal, never a live host
            await app.state.gateway.connections["mirror-1"].socket.close(code=1012)
            await until(lambda: not runtime.connected.is_set())
            clock.advance(2)
            await until(lambda: len(speaker.completed) == 2 and not runtime.voice.player.busy)
            assert not stt.calls and not tts.calls and app.state.agent.provider is None
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

        restarted_speaker = Speaker()
        restarted = EdgeRuntime(
            edge_settings(tmp_path, port),
            SimulatedHardware(),
            audio_source=Microphone(),
            detector=Detector(),
            speaker=restarted_speaker,
            voice_utc_clock=clock,
        )
        restarted_task = asyncio.create_task(restarted.run())
        try:
            await asyncio.wait_for(restarted.connected.wait(), 5)
            async with asyncio.timeout(5):
                while True:  # noqa: ASYNC110 -- observe durable output receipts after reconnect
                    state = await app.state.voice.alarm_snapshot(owner)
                    if len(state["alarms"]) == 2 and all(
                        row["delivery_status"] == "completed" for row in state["alarms"]
                    ):
                        break
                    await asyncio.sleep(0.01)
            assert not restarted_speaker.calls
            assert all(
                row["pending"] for row in state["alarms"]
            )  # playback does not acknowledge timers
        finally:
            restarted_task.cancel()
            await asyncio.gather(restarted_task, return_exceptions=True)

    # Backend storage and the edge's attempt receipts both survive a process restart.
    async with live_server(settings, service_clock=clock, speech_stt=STT(), speech_tts=TTS()) as (
        app,
        port,
    ):
        speaker = Speaker()
        runtime = EdgeRuntime(
            edge_settings(tmp_path, port),
            SimulatedHardware(),
            audio_source=Microphone(),
            detector=Detector(),
            speaker=speaker,
            voice_utc_clock=clock,
        )
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            await until(
                lambda: bool(app.state.voice.sync_pending.get("mirror-1", {}).get("stored"))
            )
            alarms = (await app.state.services.timers.list(owner))["alarms"]
            assert len(alarms) == 2 and not speaker.calls
            for alarm in alarms:
                await runtime.voice.dismiss(UUID(alarm["alarm_id"]))
            async with asyncio.timeout(5):
                while (await app.state.services.timers.list(owner))["alarms"]:  # noqa: ASYNC110
                    await asyncio.sleep(0.01)
            timers = await app.state.services.timers.list(owner, include_finished=True)
            assert {row["id"] for row in timers["timers"]} == set(identities)
            assert all(row["status"] == "ACKNOWLEDGED" for row in timers["timers"])
            assert not speaker.calls
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
