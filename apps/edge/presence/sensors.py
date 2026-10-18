"""Sensor lifecycle boundary. A simulated source is never a physical observation."""

import asyncio
from typing import Protocol

from packages.presence import PresenceReading


class PresenceSensor(Protocol):
    """A read must honor cancellation; the supervisor enforces read_timeout.

    Future UART implementations own only their separately configured sensor port.
    No sensor may discover, open, or configure the Feather data interface.
    """

    async def initialize(self) -> None: ...
    async def read(self) -> PresenceReading: ...
    async def close(self) -> None: ...


class UnavailableSensor:
    async def initialize(self):
        pass

    async def read(self):
        return PresenceReading()

    async def close(self):
        pass


class SimulatedSensor:
    def __init__(self):
        self.reading = PresenceReading()
        self.connected = False
        self.changed = asyncio.Event()

    async def initialize(self):
        self.connected = True

    def feed(self, state, health="healthy"):
        self.reading = PresenceReading(state=state, health=health)
        self.changed.set()

    async def read(self):
        if not self.connected:
            return PresenceReading()
        return self.reading

    async def close(self):
        self.connected = False
