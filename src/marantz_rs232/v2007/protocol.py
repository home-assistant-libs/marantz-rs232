"""Wire-format encoding/decoding for the legacy (`@CMD:VALUE\\r`) protocol."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass

VOLUME_MUTE_SENTINEL = "-ZZZ"  # what the receiver returns when fully muted


def encode_volume(db: float) -> str:
    """Encode a volume value (dB) for the `@VOL:0xxxy` set command.

    The leading `0` operator is added by the caller. This returns just the
    `xxxy` portion: signed 3-character whole part plus optional half-dB digit.

    -13.5 → "-135", -13.0 → "-130", 0.5 → "+005", +18.0 → "+180".
    """
    if math.isinf(db) or db <= -80.5:
        return VOLUME_MUTE_SENTINEL
    if db > 18.0:
        raise ValueError(f"Volume {db} above max +18.0 dB")

    whole_part = math.trunc(db)
    fractional = abs(db) - abs(whole_part)
    half_digit = "5" if fractional >= 0.5 else "0"

    sign = "-" if db < 0 or (db == 0 and math.copysign(1, db) == -1) else "+"
    return f"{sign}{abs(whole_part):02d}{half_digit}"


def parse_volume(value: str) -> float:
    """Parse a `VOL:` response payload into a float dB value.

    Accepts 3-character whole values (`"000"`, `"-13"`, `"+18"`) and 4-character
    half-dB values (`"+005"`, `"-135"`, `"-130"`). The `-ZZZ` sentinel maps to
    -inf (full mute). Tolerates leading whitespace (some firmwares pad).
    """
    value = value.strip()
    if value == VOLUME_MUTE_SENTINEL:
        return float("-inf")

    if len(value) >= 4 and value[-1] in ("0", "5"):
        whole = int(value[:-1])
        half = 0.5 if value[-1] == "5" else 0.0
        if whole < 0:
            return whole - half
        return whole + half

    return float(int(value))


def encode_tone(db: int) -> str:
    """Encode a bass/treble value into the signed 3-char form, e.g. `+06`/`-03`/`+00`."""
    sign = "+" if db >= 0 else "-"
    return f"{sign}{abs(db):02d}"


def parse_tone(value: str) -> int:
    """Parse a TOB/TOT response value, tolerating firmware-emitted leading whitespace."""
    return int(value.strip())


def encode_tuner_frequency_am_khz(khz: int) -> str:
    """Encode an AM frequency (1-1999 kHz) for `@TFQ:0xxxxx`."""
    if not 1 <= khz < 2000:
        raise ValueError("AM frequency must be 1..1999 kHz")
    return f"{khz:05d}"


def encode_tuner_frequency_fm_mhz(mhz: float) -> str:
    """Encode an FM frequency (>= 20.00 MHz) for `@TFQ:0xxxxx` (10 kHz units)."""
    units = round(mhz * 100)
    if units < 2000:
        raise ValueError("FM frequency must be at least 20.00 MHz")
    if units > 99999:
        raise ValueError("FM frequency too high")
    return f"{units:05d}"


def encode_tuner_xm_channel(channel: int) -> str:
    """Encode an XM channel (0-255) for `@TFQ:0xxxxx`."""
    if not 0 <= channel < 256:
        raise ValueError("XM channel must be 0..255")
    return f"{channel:05d}"


def decode_tuner_frequency(raw: str) -> tuple[str, float]:
    """Decode a `TFQ:` raw 5-digit response into `(band, value)`.

    Returns one of:
    - `("XM", channel)` for `1..255`
    - `("AM", kHz)` for `256..1999`
    - `("FM", MHz)` for `2000..10800` (10 kHz units)

    Raises `ValueError` for sentinel/uninitialised values like `00000` or
    `65535` (out of valid FM range), or anything else that doesn't decode.
    """
    units = int(raw)
    if units == 0:
        raise ValueError("Tuner not tuned (00000)")
    if units < 256:
        return "XM", float(units)
    if units < 2000:
        return "AM", float(units)
    if units > 10800:
        raise ValueError(f"Tuner frequency out of range: {raw}")
    return "FM", units / 100.0


def encode_lip_sync(ms: int) -> str:
    """Encode a lip-sync delay (0-200 ms in 10 ms steps) for `@LIP:0xxx`."""
    if ms < 0 or ms > 200:
        raise ValueError("Lip sync must be 0..200 ms")
    if ms % 10 != 0:
        raise ValueError("Lip sync must be a multiple of 10 ms")
    return f"{ms:03d}"


def encode_set_command(prefix: str, payload: str) -> bytes:
    """Build the wire-format bytes for a set command: `@<prefix>:<payload>\\r`."""
    return f"@{prefix}:{payload}\r".encode("ascii")


def encode_set_command_b(prefix: str, payload: str) -> bytes:
    """Build the wire-format bytes for a Multi Room B set command (`=` separator).

    SR8002 only.
    """
    return f"@{prefix}={payload}\r".encode("ascii")


def encode_query(prefix: str) -> bytes:
    """Build the wire-format bytes for a query: `@<prefix>:?\\r`."""
    return f"@{prefix}:?\r".encode("ascii")


def encode_query_b(prefix: str) -> bytes:
    """Build the wire-format bytes for a Multi Room B query (`=` separator)."""
    return f"@{prefix}=?\r".encode("ascii")


def parse_line(line: str) -> tuple[str, str, str] | None:
    """Parse a single received line.

    Strips a leading `@`, a trailing CR/LF, and splits on the first `:`, `=`,
    or `*` separator. Returns `(prefix, separator, value)` or `None` for ACK/NAK
    or unparseable input. The separator distinguishes Multi Room A (`:`),
    Multi Room B (`=`), and HD Radio metadata (`*`).
    """
    text = line.strip().lstrip("@")
    if not text:
        return None
    # ACK / NAK are single-byte payloads.
    if text in ("\x06", "\x15"):
        return None
    for sep in (":", "=", "*"):
        if sep in text:
            prefix, _, value = text.partition(sep)
            return prefix, sep, value
    return None


@dataclass
class PendingQuery:
    prefix: str
    future: asyncio.Future[str]
    separator: str = ":"  # ":" main / MR-A, "=" MR-B, "*" HD Radio metadata
