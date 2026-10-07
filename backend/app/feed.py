import base64
import json
import zlib


def decode_compressed(payload: str):
    raw = base64.b64decode(payload)
    last_error = None
    for bits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
        try:
            return json.loads(zlib.decompress(raw, bits))
        except Exception as error:
            last_error = error
    raise ValueError("Could not decode timing payload") from last_error


def parse_frames(buffer: str):
    parts = buffer.split("\x1e")
    leftover = parts.pop() if parts else ""
    messages = []
    for part in parts:
        if not part:
            continue
        messages.append(json.loads(part))
    return messages, leftover
