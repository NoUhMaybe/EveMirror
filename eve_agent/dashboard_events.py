import json
import socket
from typing import Any, Dict

UDP_HOST = "127.0.0.1"
UDP_PORT = 8766


def emit_event(event_type: str, payload: Dict[str, Any]) -> None:
    message = {
        "type": event_type,
        "payload": payload,
    }
    data = json.dumps(message).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(data, (UDP_HOST, UDP_PORT))
