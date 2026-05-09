"""Constants and enums for the v2003 (SR9300/SR8300) Marantz protocol.

Reference: docs/Marantz 2003 SR9300 SR8300 RS232C Control Specification v2.00.pdf

Wire format: ``@<ID><code>\\r``. Device IDs are ``'0'`` through ``'9'``; the
host must use the ID the receiver was configured with. Default is ``'1'``.

Many command codes overlap with status answer codes but mean different things
in each direction. ``A0`` *as a command* means POWER toggle, but ``A0`` *as a
status answer* means POWER ON. The enum values below all carry the bytes that
appear on the wire — `V2003Power.ON.command` is what you send, while the
parser maps received status codes back into enum members via
:data:`POWER_STATUS_CODES`.
"""

from __future__ import annotations

from enum import Enum

V2003_BAUD_RATE = 4800
V2003_COMMAND_TIMEOUT = 1.5  # spec says 1 s; give a small margin
V2003_PREFIX = "@"
V2003_TERMINATOR = b"\r"

ACK_BYTE = b"\x06"
NAK_BYTE = b"\x15"

DEFAULT_DEVICE_ID = "1"


class V2003Power(Enum):
    """Power command codes. Status answers use a *different* mapping —
    see :data:`POWER_STATUS_CODES`.
    """

    TOGGLE = "A0"
    ON = "A1"
    OFF = "A2"


# Status-answer interpretation of A0/A1.
POWER_STATUS_CODES: dict[str, bool] = {
    "A0": True,   # POWER ON
    "A1": False,  # POWER OFF
}


class V2003Source(Enum):
    """Logical input source. The enum value is the *set-command position* —
    the second character of a B-prefix command (``B3`` for DVD, ``BG`` for
    TUNER). For most sources this also matches the status-answer position,
    but the spec is asymmetric for the last two slots:

    * Audio status ``CG`` is "multi-channel input" (a path mode, not a real
      source) — modelled as the boolean :attr:`V2003MainState.multi_channel_input`.
    * Audio status ``CH`` is TUNER (vs the ``BG`` set command for TUNER).
    * Multi-room audio status skips ``ZC``; FM..LW shift up by one (``ZD``..``ZG``)
      and TUNER lives at ``ZH``.

    The codecs in :mod:`.protocol` handle this asymmetry — callers stick to
    this enum.
    """

    DSS = "0"
    TV = "1"
    LD = "2"
    DVD = "3"
    VCR1 = "4"
    VCR2_DVDR = "5"
    AUX1 = "6"
    AUX2 = "7"
    DVDR = "8"
    CD = "9"
    TAPE = "A"
    CDR = "B"
    FM = "C"
    AM = "D"
    MW = "E"
    LW = "F"
    TUNER = "G"


# Audio-only sources (cannot be reported as a video input).
AUDIO_ONLY_SOURCES = frozenset(
    {
        V2003Source.CD,
        V2003Source.TAPE,
        V2003Source.CDR,
        V2003Source.FM,
        V2003Source.AM,
        V2003Source.MW,
        V2003Source.LW,
        V2003Source.TUNER,
    }
)


class V2003InputMode(Enum):
    """Status answer for ?D (digital vs analogue input mode)."""

    DIGITAL = "D0"
    ANALOGUE = "D1"


class V2003TunerMode(Enum):
    """Status answer for ?G."""

    MONO = "G0"
    AUTO_STEREO = "G1"


class V2003TunerBand(Enum):
    """Tuner band. Inferred from the audio input source (FM/AM/MW/LW)
    rather than reported by a dedicated query.
    """

    FM = "FM"
    AM = "AM"
    MW = "MW"
    LW = "LW"


class V2003SurroundMode(Enum):
    """Surround mode. Used for both commands (``F<code>``) and status
    answers (``L<code>``); the second character is what we store.

    The wire format differs by direction (`F0` to set Auto, `L0` in a
    response). The encoder in :mod:`.protocol` adds the right prefix.
    """

    AUTO = "0"
    THX_5_1 = "1"            # status answer "L1"; command "F1" is THX MUSIC per the spec
    THX_SURR_EX = "2"
    THX_CINEMA = "3"
    THX_MUSIC = "4"
    DTS_MUSIC = "5"
    DTS_CINEMA = "6"
    DTS_ES = "7"
    NEO6_CINEMA = "8"
    NEO6_MUSIC = "9"
    DOLBY_DIGITAL = "A"
    DOLBY_PROLOGIC = "B"
    DOLBY_PLII_MOVIE = "C"
    DOLBY_PLII_MUSIC = "D"
    CSII_CINEMA = "E"
    CSII_MUSIC = "F"
    VIRTUAL = "G"
    S_DIRECT = "H"
    MOVIE = "I"
    HALL = "J"
    MATRIX = "K"
    MCH_STEREO = "L"
    STEREO = "M"
    MONO = "N"
    THX_ULTRA2 = "O"
    CSII_MONO = "P"


class V2003SignalFormat(Enum):
    """Status answer for ?U."""

    NONE = "0"
    DOLBY_DIGITAL = "1"
    DOLBY_SURROUND = "2"
    DOLBY_SURR_EX = "3"
    DTS = "4"
    DTS_ES = "5"
    AAC = "6"
    MPEG = "7"
    MLP = "8"
    PCM = "9"
    HDCD = "A"
    DSD = "B"
    OTHER = "C"


class V2003SamplingFrequency(Enum):
    """Status answer for ?V (sampling rate in kHz)."""

    NONE = "0"
    KHZ_32 = "1"
    KHZ_44_1 = "2"
    KHZ_48 = "3"
    KHZ_88_2 = "4"
    KHZ_96 = "5"
    KHZ_176_4 = "6"
    KHZ_192 = "7"


class V2003TestTone(Enum):
    """Test-tone channel status (?P)."""

    OFF = "P0"
    LEFT = "P1"
    CENTER = "P2"
    RIGHT = "P3"
    SURR_RIGHT = "P4"
    SURR_BACK_RIGHT = "P5"
    SURR_BACK_LEFT = "P6"
    SURR_LEFT = "P7"
    SUBWOOFER = "P8"


class V2003TestToneMode(Enum):
    """Status answer for ?Q."""

    AUTO = "Q0"
    MANUAL = "Q1"


class V2003DisplayMode(Enum):
    """Status answer for ?N. ``DIMMER_*`` covers the N3..N9 dimmer range."""

    ON = "N0"
    OFF = "N1"
    AUTO_OFF = "N2"
    DIMMER_3 = "N3"
    DIMMER_4 = "N4"
    DIMMER_5 = "N5"
    DIMMER_6 = "N6"
    DIMMER_7 = "N7"
    DIMMER_8 = "N8"
    DIMMER_9 = "N9"


class V2003MultiRoomVolumeMode(Enum):
    """Status answer for ?d (multi-room volume mode)."""

    VARIABLE = "d0"
    FIXED = "d1"


# Useful for human-friendly logging / CLI display.
V2003_SOURCE_NAMES: dict[str, str] = {
    member.value: member.name for member in V2003Source
}

V2003_SURROUND_NAMES: dict[str, str] = {
    member.value: member.name for member in V2003SurroundMode
}
