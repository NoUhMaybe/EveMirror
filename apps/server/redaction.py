from pydantic import SecretStr


def redact(value, secrets):
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[redacted]")
        return value
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, dict):
        return {redact(key, secrets): redact(item, secrets) for key, item in value.items()}
    return value


def secret_redactor(settings):
    values = []

    def collect(value):
        if isinstance(value, SecretStr):
            values.append(value.get_secret_value())
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(settings.model_dump(mode="python"))
    values = sorted(set(values), key=len, reverse=True)
    return lambda value: redact(value, values)
