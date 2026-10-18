"""Pure source-value helpers shared by the migrated and retained weather consumers."""

import math

CONDITIONS = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "light freezing drizzle",
    57: "freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "rain showers",
    81: "heavy rain showers",
    82: "violent rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "heavy hailstorm",
}


def number(value):
    return (
        float(value)
        if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)
        else None
    )


def condition(value):
    code = number(value)
    return CONDITIONS.get(code, f"weather code {code:g}") if code is not None else None


def column(source, key, index):
    values = source.get(key)
    return number(values[index]) if isinstance(values, list) and index < len(values) else None
