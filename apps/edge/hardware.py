"""Sole serial owner. Preserve the deployed firmware's electrical behavior."""

from __future__ import annotations

import asyncio
import os
import re
import time
from collections.abc import Callable
from typing import Any

from packages.protocol import HardwareStatus


class HardwareError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def clamp_brightness(percent: int) -> int:
    if type(percent) is not int:
        raise ValueError("Brightness must be an integer")
    return max(0, min(100, percent))


class FeatherService:
    def __init__(
        self,
        port: str | None = None,
        timeout: float = 1,
        serial_factory: Callable[..., Any] | None = None,
    ):
        self.port = port
        self.timeout = timeout
        self._factory = serial_factory
        self._serial = None
        self._lock = asyncio.Lock()
        self._status = HardwareStatus()

    @property
    def status(self) -> HardwareStatus:
        return self._status

    def _open(self):
        if self._factory is None:
            import serial

            self._factory = serial.Serial
        port = self.port
        if port is None:
            from serial.tools import list_ports

            matches = [
                p.device
                for p in list_ports.comports()
                if p.vid == 0x239A and "data" in (p.interface or "").lower()
            ]
            if len(matches) != 1:
                raise HardwareError("unavailable")
            port = matches[0]
        self._serial = self._factory(
            port=port,
            baudrate=115200,
            timeout=self.timeout,
            write_timeout=self.timeout,
            **({"exclusive": True} if os.name == "posix" else {}),
        )
        time.sleep(0.2)  # preserve the legacy client's CDC settle time

    def _close(self):
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None
        self._status = self._status.model_copy(update={"connected": False})

    def _set(self, percent: int) -> HardwareStatus:
        wrote = False
        try:
            if self._serial is None:
                self._open()
            self._serial.reset_input_buffer()
            # Once a write starts, a failed/missing ACK cannot prove no action occurred.
            wrote = True
            data = f"B{percent}\n".encode("ascii")
            if self._serial.write(data) != len(data):
                raise HardwareError("indeterminate")
            reply = self._serial.readline(80)
            match = re.fullmatch(rb"OK (\d{1,3})\r?\n", reply)
            if not match or int(match[1]) != percent:
                raise HardwareError("invalid_ack")
            self._status = HardwareStatus(connected=True, target_percent=percent)
            return self._status
        except Exception as exc:
            try:
                self._close()
            except Exception:
                pass
            self._status = HardwareStatus()
            if isinstance(exc, HardwareError):
                raise
            raise HardwareError("indeterminate" if wrote else "unavailable") from None

    async def set_brightness(self, percent: int) -> HardwareStatus:
        percent = clamp_brightness(percent)
        async with self._lock:
            # Shield the worker and wait for it before releasing the serial lock on cancellation.
            worker = asyncio.create_task(asyncio.to_thread(self._set, percent))
            try:
                return await asyncio.shield(worker)
            except asyncio.CancelledError:
                try:
                    await worker
                except HardwareError:
                    pass
                raise

    async def close(self):
        async with self._lock:
            await asyncio.to_thread(self._close)


class SimulatedHardware:
    """Explicit simulation. Never represents a physical measurement."""

    def __init__(self):
        self.status = HardwareStatus(connected=True, simulated=True)
        self.commands: list[int] = []

    async def set_brightness(self, percent: int) -> HardwareStatus:
        self.commands.append(clamp_brightness(percent))
        self.status = HardwareStatus(
            connected=True,
            target_percent=self.commands[-1],
            simulated=True,
        )
        return self.status

    async def close(self):
        self.status = self.status.model_copy(update={"connected": False})
