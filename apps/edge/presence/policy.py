"""Pure monotonic presence state machine. Wall time is used only for schedules."""

from packages.presence import PresenceOptions, PresenceReading


class PresenceMachine:
    def __init__(self, settings: PresenceOptions, now: float):
        self.settings = settings
        self.reading = PresenceReading()
        self.confirmed = "UNKNOWN"
        self.candidate = "UNKNOWN"
        self.candidate_since = now
        self.absent_since = None
        self.awake_since = now
        self.last_wake = float("-inf")
        self.target = None
        self.manual = None
        self.manual_until = now
        self.activity = set()
        self.grace_until = now

    def observe(self, reading: PresenceReading, now: float):
        self.reading = reading
        state = reading.state
        if state == "UNKNOWN":
            # Unknown breaks every absence/presence continuity, including timeouts.
            self.confirmed = self.candidate = "UNKNOWN"
            self.absent_since = None
            self.candidate_since = now
            return
        if state != self.candidate:
            self.candidate, self.candidate_since = state, now
        delay = (
            self.settings.present_confirm if state == "PRESENT" else self.settings.absent_confirm
        )
        if now - self.candidate_since >= delay and self.confirmed != state:
            self.confirmed = state
            self.absent_since = now if state == "ABSENT" else None

    def protect(self, name: str, active: bool, now: float):
        if active:
            self.activity.add(name)
        elif name in self.activity:
            self.activity.remove(name)
            self.grace_until = max(self.grace_until, now + self.settings.activity_grace)

    def override(self, percent: int, now: float):
        self.manual, self.manual_until = percent, now + self.settings.manual_override_seconds

    def choose(self, now, wall):
        options = self.settings
        if self.manual is not None and now < self.manual_until:
            return self.manual, "manual"
        self.manual = None
        if self.activity or now < self.grace_until:
            return options.preferred_percent, "activity"
        if options.enabled:
            if self.confirmed == "UNKNOWN":
                if options.unknown_policy == "hold" and self.target is not None:
                    return self.target, "unknown"
                return options.preferred_percent, "unknown"
            asleep = (
                self.confirmed == "ABSENT"
                and self.absent_since is not None
                and now - self.absent_since >= options.absence_timeout
                and now - self.awake_since >= options.minimum_awake
            )
            if asleep:
                return 0, "presence"
            if self.target == 0 and self.confirmed != "PRESENT":
                return 0, "presence"
            if self.target == 0 and now - self.last_wake < options.wake_cooldown:
                return 0, "presence"
        if options.night.active(wall):
            return min(options.preferred_percent, options.night.percent), "night"
        return options.preferred_percent, "presence" if options.enabled else "default"

    def selected(self, percent, now):
        if percent > 0 and (self.target is None or self.target == 0):
            self.awake_since = self.last_wake = now
        self.target = percent
