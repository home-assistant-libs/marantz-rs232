"""Wire-format encoding/decoding for the v2003 protocol.

Frame format on the wire is ``@<ID><CODE>\\r``. ``<ID>`` is one ASCII digit
(``'0'``..``'9'``); ``<CODE>`` is a 2- or 3+ character payload. ACK and NAK
responses are bare ``0x06`` / ``0x15`` bytes (no ``@`` wrapper, unlike v2007).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .const import V2003Source, V2003TunerBand


def encode_command(device_id: str, code: str) -> bytes:
    """Build wire bytes for a normal command. ``code`` is e.g. ``"A1"`` or
    ``"H02"`` (volume = +2 dB).
    """
    return f"@{device_id}{code}\r".encode("ascii")


def encode_query(device_id: str, request_char: str) -> bytes:
    """Build wire bytes for a status request: ``@<ID>?<char>\\r``.

    ``request_char`` is the single status-request letter (``'A'`` for power,
    ``'H'`` for volume, etc.). Some queries use a two-character form
    (``?i0``..``?i7`` for channel levels) — pass the full string in that case.
    """
    return f"@{device_id}?{request_char}\r".encode("ascii")


def parse_line(
    line: str,
    *,
    expected_id: str | None = None,
) -> tuple[str, str] | None:
    """Parse one received line into ``(device_id, payload)``.

    Returns ``None`` for empty input or for a line with the wrong device ID
    (when ``expected_id`` is provided). ACK / NAK are byte-level and never
    reach this function — they are handled in the read loop.
    """
    text = line.strip()
    if not text or not text.startswith("@") or len(text) < 3:
        return None
    device_id = text[1]
    payload = text[2:]
    if expected_id is not None and device_id != expected_id:
        return None
    return device_id, payload


# -- Source code conversion ---------------------------------------------------

_SOURCE_POSITIONS = "0123456789ABCDEFGH"  # 0..9, A..H — index of each source
_MULTI_INPUT_LETTERS = "abcdefghijklmnopq"  # multi-room set codes Ba..Bq


def encode_main_source(source: V2003Source) -> str:
    """Wire code (without the leading ``@<ID>``) to set the main-room input.

    Returns e.g. ``"B3"`` for DVD or ``"BG"`` for TUNER.
    """
    return f"B{source.value}"


def encode_multi_source(source: V2003Source) -> str:
    """Wire code to set the *multi-room* input.

    The multi-room aliases are lowercase letters ``a``..``q`` — for example
    ``Bd`` selects DVD in the multi room (corresponding to ``B3`` in the main
    room).
    """
    idx = _SOURCE_POSITIONS.index(source.value)
    return f"B{_MULTI_INPUT_LETTERS[idx]}"


def decode_video_source(payload: str) -> V2003Source | None:
    """Parse a video-input status answer (``B0``..``B8`` → DSS..DVD-R).

    Returns ``None`` for the ``B-`` not-available sentinel or any unknown
    code (video inputs only cover positions 0..8).
    """
    if not payload or len(payload) != 2 or payload[0] != "B":
        return None
    if payload[1] == "-":
        return None
    if payload[1] not in "012345678":
        return None
    try:
        return V2003Source(payload[1])
    except ValueError:
        return None


def is_main_multi_channel_input(payload: str) -> bool:
    """``True`` when the audio-status answer is ``CG``, indicating that the
    main-zone audio is currently coming from the analog multi-channel input.
    """
    return payload == "CG"


def decode_audio_source(payload: str) -> V2003Source | None:
    """Parse a main-zone audio-input status answer (``C0``..``CH``).

    Returns ``None`` for ``C-`` (not available) and ``CG`` (multi-channel
    input — check :func:`is_main_multi_channel_input`). ``CH`` decodes as
    :attr:`V2003Source.TUNER`, which is at position ``G`` in the set-command
    space — the spec is asymmetric here.
    """
    if not payload or len(payload) != 2 or payload[0] != "C":
        return None
    pos = payload[1]
    if pos == "-" or pos == "G":
        return None
    if pos == "H":
        return V2003Source.TUNER
    try:
        return V2003Source(pos)
    except ValueError:
        return None


def decode_multi_video_source(payload: str) -> V2003Source | None:
    """Parse a multi-room video-input status answer (``Y0``..``Y8``)."""
    if not payload or len(payload) != 2 or payload[0] != "Y":
        return None
    if payload[1] == "-":
        return None
    if payload[1] not in "012345678":
        return None
    try:
        return V2003Source(payload[1])
    except ValueError:
        return None


# Multi-room audio status skips ZC; FM..LW shift up to ZD..ZG, TUNER at ZH.
_MULTI_AUDIO_POSITION_TO_SOURCE: dict[str, V2003Source] = {
    "0": V2003Source.DSS,
    "1": V2003Source.TV,
    "2": V2003Source.LD,
    "3": V2003Source.DVD,
    "4": V2003Source.VCR1,
    "5": V2003Source.VCR2_DVDR,
    "6": V2003Source.AUX1,
    "7": V2003Source.AUX2,
    "8": V2003Source.DVDR,
    "9": V2003Source.CD,
    "A": V2003Source.TAPE,
    "B": V2003Source.CDR,
    # "C" is intentionally absent — see the spec asymmetry note.
    "D": V2003Source.FM,
    "E": V2003Source.AM,
    "F": V2003Source.MW,
    "G": V2003Source.LW,
    "H": V2003Source.TUNER,
}


def decode_multi_audio_source(payload: str) -> V2003Source | None:
    """Parse a multi-room audio-input status answer (``Z0``..``Z9``, ``ZA``,
    ``ZB``, ``ZD``..``ZH``). Returns ``None`` for ``Z-`` and unknown codes.
    """
    if not payload or len(payload) != 2 or payload[0] != "Z":
        return None
    return _MULTI_AUDIO_POSITION_TO_SOURCE.get(payload[1])


# -- Volume -------------------------------------------------------------------


def encode_volume(db: int) -> str:
    """Encode an absolute volume level for the ``H0XXX`` command form.

    Range is -90..+99 dB, integer steps only (the spec doesn't define
    half-dB on the wire). Mute is sent via the dedicated H1/H2 commands —
    pass ``-inf`` to this function and you get a ValueError.
    """
    if not -90 <= db <= 99:
        raise ValueError(f"Volume {db} dB out of range -90..+99")
    sign = "+" if db >= 0 else "-"
    return f"H0{sign}{abs(db):02d}"


def parse_volume(payload: str) -> tuple[float, bool]:
    """Parse an ``H...`` status answer.

    Returns ``(db, muted)``. ``H0XXX`` → ``(int(XXX), False)``,
    ``H1`` → ``(99, False)`` (max), ``H2`` → ``(-inf, True)`` (-∞).
    Raises ``ValueError`` for malformed input.
    """
    if payload == "H1":
        return (99.0, False)
    if payload == "H2":
        return (float("-inf"), True)
    if not payload.startswith("H0") or len(payload) < 5:
        raise ValueError(f"Cannot parse volume answer: {payload!r}")
    return (float(int(payload[2:])), False)


def parse_multi_volume(payload: str) -> tuple[float, bool]:
    """Parse a ``c...`` (multi-room volume) status answer."""
    if payload == "c1":
        return (99.0, False)
    if payload == "c2":
        return (float("-inf"), True)
    if not payload.startswith("c0") or len(payload) < 5:
        raise ValueError(f"Cannot parse multi-room volume answer: {payload!r}")
    return (float(int(payload[2:])), False)


# -- Tone (bass / treble) -----------------------------------------------------


def encode_tone(db: int) -> str:
    """Encode a signed -9..+9 dB value used in I0xx / J0xx answers.

    Note: there's no SET command for absolute tone in this protocol —
    only G4..G7 step commands. This helper exists for parsing parity.
    """
    if not -9 <= db <= 9:
        raise ValueError(f"Tone {db} dB out of range -9..+9")
    sign = "+" if db >= 0 else "-"
    return f"{sign}{abs(db):02d}"


def parse_tone(payload: str) -> int:
    """Parse an ``I0xx`` or ``J0xx`` payload."""
    if len(payload) < 5 or payload[1] != "0":
        raise ValueError(f"Cannot parse tone: {payload!r}")
    return int(payload[2:])


# -- Tuner --------------------------------------------------------------------


def decode_tuner_frequency(
    payload: str,
    band: V2003TunerBand | None = None,
) -> tuple[V2003TunerBand, float] | None:
    """Decode an ``E0XXXX`` (or ``a0XXXX`` for multi-room) tuner-frequency
    answer. ``XXXX`` is 4 ASCII digits.

    The encoding is band-dependent and the band is *not* in the response —
    pass it explicitly (e.g. derived from the current audio source). If
    ``band`` is ``None`` we infer from the numeric range, but that's a guess.

    Returns ``None`` for the ``E-`` / ``a-`` not-available sentinels.

    FM is encoded in 10-kHz units modulo 10000: ``87.50`` → ``"8750"``,
    ``108.00`` → ``"0800"`` (overflow). AM/MW are kHz; LW is kHz.
    """
    if payload in ("E-", "a-"):
        return None
    if len(payload) != 6 or payload[1] != "0":
        raise ValueError(f"Cannot parse tuner frequency: {payload!r}")
    raw = int(payload[2:])

    if band is None:
        band = _infer_tuner_band(raw)

    if band is V2003TunerBand.FM:
        # Wraparound: values 0..800 mean 100.00..108.00 MHz.
        if raw < 7000:
            raw += 10000
        return (band, raw / 100.0)
    if band in (V2003TunerBand.AM, V2003TunerBand.MW, V2003TunerBand.LW):
        return (band, float(raw))
    return (band, float(raw))


def _infer_tuner_band(raw: int) -> V2003TunerBand:
    if 152 <= raw <= 282:
        return V2003TunerBand.LW
    if 520 <= raw <= 1710:
        return V2003TunerBand.AM
    # everything else assume FM (with possible overflow)
    return V2003TunerBand.FM


def decode_tuner_preset(payload: str) -> int | None:
    """``F0XX`` → preset number 1..50, ``F000`` → not in preset mode,
    ``F-`` → not available.
    """
    if payload == "F-":
        return None
    if not payload.startswith("F0") or len(payload) != 4:
        raise ValueError(f"Cannot parse tuner preset: {payload!r}")
    n = int(payload[2:])
    return n if n > 0 else None


def decode_multi_tuner_preset(payload: str) -> int | None:
    if payload == "b-":
        return None
    if not payload.startswith("b0") or len(payload) != 4:
        raise ValueError(f"Cannot parse multi-room tuner preset: {payload!r}")
    n = int(payload[2:])
    return n if n > 0 else None


# -- Sleep timer --------------------------------------------------------------


def parse_sleep(payload: str) -> int | None:
    """``M0`` → 0 (off), ``M1XXX`` → minutes."""
    if payload == "M0":
        return 0
    if payload.startswith("M1") and len(payload) == 5:
        return int(payload[2:])
    raise ValueError(f"Cannot parse sleep: {payload!r}")


def parse_multi_sleep(payload: str) -> int | None:
    if payload == "e0":
        return 0
    if payload.startswith("e1") and len(payload) == 5:
        return int(payload[2:])
    raise ValueError(f"Cannot parse multi-room sleep: {payload!r}")


@dataclass
class PendingQuery:
    request_char: str  # the ?-letter we sent (e.g. "A", "H")
    future: asyncio.Future[str]
