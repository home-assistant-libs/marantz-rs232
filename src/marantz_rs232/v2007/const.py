"""Constants and enums for the v2007 (SR7002-era) Marantz protocol."""

from enum import Enum

V2007_BAUD_RATE = 9600
V2007_COMMAND_TIMEOUT = 1.0  # spec mandates response within 500 ms; 1 s for safety

V2007_PREFIX = "@"
V2007_SEPARATOR = ":"
V2007_TERMINATOR = b"\r"
V2007_MULTI_ROOM_B_SEPARATOR = "="  # SR8002 Multi Room B substitutes `=` for `:`
# `*` carries two unrelated payload kinds: HD Radio metadata responses (AV8003,
# SR8002, SR7002) and TUNER2 commands/responses (SR9600, SR9600A).
V2007_HD_RADIO_SEPARATOR = "*"
V2007_TUNER2_SEPARATOR = "*"
# `#` is Multi-Zone B + TUNER2 — SR9600/SR9600A only.
V2007_MR_B_TUNER2_SEPARATOR = "#"

# Single-byte ACK / NAK responses framed as `@\x06\r` / `@\x15\r`.
ACK_BYTE = "\x06"
NAK_BYTE = "\x15"


class V2007Model(Enum):
    """Specific Marantz model in the v2007 protocol family.

    Models are grouped by feature set; see :data:`V2007_SUPPORTED_SOURCES`,
    :data:`V2007_HD_RADIO_MODELS`, :data:`V2007_MULTI_ROOM_B_MODELS`,
    :data:`V2007_TUNER2_MODELS`, and :data:`V2007_COMPONENT2_MODELS` for the
    per-feature model sets.

    GENERIC is a safe baseline assuming nothing model-specific.
    """

    GENERIC = "generic"
    AV8003 = "AV8003"
    SR9600 = "SR9600"
    SR9600A = "SR9600A"
    SR8002 = "SR8002"
    SR7002 = "SR7002"
    SR8001 = "SR8001"
    SR7001 = "SR7001"
    SR8500 = "SR8500"
    SR7500 = "SR7500"
    SR6004 = "SR6004"
    SR5004 = "SR5004"
    SR6003 = "SR6003"
    SR5003 = "SR5003"
    SR5002 = "SR5002"
    SR6001 = "SR6001"
    SR5001 = "SR5001"
    SR5500 = "SR5500"
    SR5600 = "SR5600"
    ZR6001 = "ZR6001"
    SR4023 = "SR4023"


# Models that respond to HD Radio metadata queries (`@CHN*`, `@ARN*`, `@SON*`,
# `@CTN*`, `@SST*`). Source: docs/Marantz_RS232C_Command_List-Receiver_All.xls.
V2007_HD_RADIO_MODELS: frozenset[V2007Model] = frozenset(
    {V2007Model.AV8003, V2007Model.SR8002, V2007Model.SR7002}
)

# Models that support Multi Room B (`=` separator).
V2007_MULTI_ROOM_B_MODELS: frozenset[V2007Model] = frozenset(
    {V2007Model.SR8002, V2007Model.SR9600, V2007Model.SR9600A}
)

# Models with a second tuner — TUNER2 commands use the `*` separator and the
# `#` separator routes to Multi-Zone B TUNER2.
V2007_TUNER2_MODELS: frozenset[V2007Model] = frozenset(
    {V2007Model.SR9600, V2007Model.SR9600A}
)

# Models that accept the Component2 video select (`@CM2:` ).
V2007_COMPONENT2_MODELS: frozenset[V2007Model] = frozenset({V2007Model.SR8002})


class V2007TriState(Enum):
    """Standard tri-state value used for many on/off-with-toggle commands.

    Applies to AMT (audio mute), VMT (video mute), ATT (attenuator),
    71C (7.1 ch input), MNU (menu), TPI (preset info), TTO (test tone).
    """

    TOGGLE = "0"
    OFF = "1"
    ON = "2"


class V2007Power(Enum):
    """PWR set values."""

    TOGGLE = "0"
    OFF = "1"
    ON = "2"
    GLOBAL_OFF = "3"


class V2007Source(Enum):
    """Wire-code source IDs for the v2007 protocol.

    The wire format is a single character. `@SRC:?` queries return TWO
    characters (video then audio) — see `V2007MainState.source_video` and
    `source_audio`. Setting via `@SRC:<code>` switches both video and audio
    to the same input.

    Names use the most common label for each code; some receivers expose the
    same code under a different name (e.g. ``J`` is "XM" on most receivers
    but "TUNER2" on SR9600, ``K`` is "SIRIUS" or "FM2", ``L`` is "AM2" or
    "PHONO"). Use :data:`V2007_SUPPORTED_SOURCES` to check which codes a
    given model actually accepts.
    """

    TV = "1"
    DVD = "2"
    VCR1 = "3"
    VCR2 = "4"
    DSS_VCR2 = "5"
    LD = "6"
    USB = "7"
    NETWORK = "8"
    AUX1 = "9"
    AUX2 = "A"
    SR4023_CD = "B"
    CD_CDR = "C"
    CD_R = "D"
    TAPE = "E"
    TUNER1 = "F"
    FM1 = "G"
    AM1 = "H"
    XM1 = "J"
    SIRIUS = "K"
    AM2 = "L"
    BD = "M"
    MXPORT = "N"


V2007_SOURCE_NAMES: dict[str, str] = {member.value: member.name for member in V2007Source}


# Per-model source support — wire codes that each model accepts on `@SRC:`.
# Source: docs/Marantz_RS232C_Command_List-Receiver_All.xls.
V2007_SUPPORTED_SOURCES: dict[V2007Model, frozenset[V2007Source]] = {
    V2007Model.AV8003: frozenset(
        {
            V2007Source.TV, V2007Source.DVD, V2007Source.VCR1, V2007Source.VCR2,
            V2007Source.DSS_VCR2, V2007Source.NETWORK, V2007Source.AUX1,
            V2007Source.CD_CDR, V2007Source.TAPE, V2007Source.TUNER1,
            V2007Source.FM1, V2007Source.AM1, V2007Source.XM1, V2007Source.SIRIUS,
        }
    ),
    V2007Model.SR9600A: frozenset(
        {
            V2007Source.TV, V2007Source.DVD, V2007Source.VCR1, V2007Source.VCR2,
            V2007Source.DSS_VCR2, V2007Source.LD, V2007Source.AUX1, V2007Source.AUX2,
            V2007Source.CD_CDR, V2007Source.CD_R, V2007Source.TAPE,
            V2007Source.TUNER1, V2007Source.FM1, V2007Source.AM1, V2007Source.XM1,
        }
    ),
    V2007Model.SR9600: frozenset(
        {
            V2007Source.TV, V2007Source.DVD, V2007Source.VCR1, V2007Source.VCR2,
            V2007Source.DSS_VCR2, V2007Source.LD, V2007Source.AUX1, V2007Source.AUX2,
            V2007Source.CD_CDR, V2007Source.CD_R, V2007Source.TAPE,
            V2007Source.TUNER1, V2007Source.FM1, V2007Source.AM1,
            V2007Source.XM1,  # labelled TUNER2 on this model
            V2007Source.SIRIUS,  # labelled FM2 on this model
            V2007Source.AM2,
        }
    ),
}
# SR8002/SR7002 share a column in the spec; same set applies to SR8001/SR7001.
_SR_8000_SOURCES = frozenset(
    {
        V2007Source.TV, V2007Source.DVD, V2007Source.VCR1, V2007Source.DSS_VCR2,
        V2007Source.AUX1, V2007Source.AUX2, V2007Source.CD_CDR, V2007Source.TAPE,
        V2007Source.TUNER1, V2007Source.FM1, V2007Source.AM1, V2007Source.XM1,
    }
)
V2007_SUPPORTED_SOURCES[V2007Model.SR8002] = _SR_8000_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.SR7002] = _SR_8000_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.SR8001] = _SR_8000_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.SR7001] = _SR_8000_SOURCES

# SR8500/SR7500 — adds CD-R, drops XM.
_SR_8500_SOURCES = frozenset(
    {
        V2007Source.TV, V2007Source.DVD, V2007Source.VCR1, V2007Source.DSS_VCR2,
        V2007Source.AUX1, V2007Source.AUX2, V2007Source.CD_CDR, V2007Source.CD_R,
        V2007Source.TAPE, V2007Source.TUNER1, V2007Source.FM1, V2007Source.AM1,
    }
)
V2007_SUPPORTED_SOURCES[V2007Model.SR8500] = _SR_8500_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.SR7500] = _SR_8500_SOURCES

# SR6004/SR5004 — USB, BD, M-XPort, no AUX2 / TAPE.
_SR_6004_SOURCES = frozenset(
    {
        V2007Source.TV, V2007Source.DVD, V2007Source.VCR1, V2007Source.VCR2,
        V2007Source.DSS_VCR2, V2007Source.USB, V2007Source.AUX1,
        V2007Source.CD_CDR, V2007Source.TUNER1, V2007Source.FM1, V2007Source.AM1,
        V2007Source.XM1, V2007Source.SIRIUS, V2007Source.BD, V2007Source.MXPORT,
    }
)
V2007_SUPPORTED_SOURCES[V2007Model.SR6004] = _SR_6004_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.SR5004] = _SR_6004_SOURCES

# SR6003/SR5003 — uses code 8 as USB.
_SR_6003_SOURCES = frozenset(
    {
        V2007Source.TV, V2007Source.DVD, V2007Source.VCR1, V2007Source.DSS_VCR2,
        V2007Source.NETWORK, V2007Source.AUX1, V2007Source.AUX2,
        V2007Source.CD_CDR, V2007Source.TAPE, V2007Source.TUNER1,
        V2007Source.FM1, V2007Source.AM1, V2007Source.XM1, V2007Source.SIRIUS,
    }
)
V2007_SUPPORTED_SOURCES[V2007Model.SR6003] = _SR_6003_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.SR5003] = _SR_6003_SOURCES

# SR5002 / SR6001 / SR5001
_SR_5002_SOURCES = frozenset(
    {
        V2007Source.TV, V2007Source.DVD, V2007Source.VCR1, V2007Source.DSS_VCR2,
        V2007Source.AUX1, V2007Source.AUX2, V2007Source.CD_CDR, V2007Source.CD_R,
        V2007Source.TAPE, V2007Source.TUNER1, V2007Source.FM1, V2007Source.AM1,
        V2007Source.XM1,
    }
)
V2007_SUPPORTED_SOURCES[V2007Model.SR5002] = _SR_5002_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.SR6001] = _SR_5002_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.SR5001] = _SR_5002_SOURCES

# SR5500/SR5600/ZR6001 — code 4 means DSS on these.
_SR_5500_SOURCES = frozenset(
    {
        V2007Source.TV, V2007Source.DVD, V2007Source.VCR1,
        V2007Source.VCR2,  # labelled DSS on this model
        V2007Source.AUX1, V2007Source.AUX2, V2007Source.CD_CDR, V2007Source.CD_R,
        V2007Source.TAPE, V2007Source.TUNER1, V2007Source.FM1, V2007Source.AM1,
    }
)
V2007_SUPPORTED_SOURCES[V2007Model.SR5500] = _SR_5500_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.SR5600] = _SR_5500_SOURCES
V2007_SUPPORTED_SOURCES[V2007Model.ZR6001] = _SR_5500_SOURCES

# SR4023 — distinct CD slot (B) and PHONO at L.
V2007_SUPPORTED_SOURCES[V2007Model.SR4023] = frozenset(
    {
        V2007Source.DVD, V2007Source.VCR1, V2007Source.DSS_VCR2,
        V2007Source.AUX1, V2007Source.SR4023_CD, V2007Source.CD_CDR,
        V2007Source.TAPE, V2007Source.TUNER1, V2007Source.FM1, V2007Source.AM1,
        V2007Source.AM2,  # labelled PHONO on this model
    }
)

# GENERIC accepts the union of all known codes — let user code send anything
# the receiver accepts.
V2007_SUPPORTED_SOURCES[V2007Model.GENERIC] = frozenset(V2007Source)


class V2007SurroundCode(Enum):
    """Surround mode status codes (single character returned by `@SUR:?`).

    These are the *status* values — the set form prepends `0` for codes
    `0`-`U` (e.g. set `@SUR:00` → status `SUR:0`). See the spec for the
    set/status asymmetry. Cycling commands use `@SUR:1` (next) and
    `@SUR:2` (prev), which don't have a status equivalent.
    """

    AUTO = "0"
    STEREO = "1"
    DOLBY = "2"
    PLIIX_MOVIE = "3"
    PLII_MOVIE = "4"
    PLIIX_MUSIC = "5"
    PLII_MUSIC = "6"
    PLIIX_GAME = "7"
    PLII_GAME = "8"
    MULTI_CH = "9"
    EX_ES = "A"
    DD_EX = "C"
    NEURAL = "D"
    DTS_ES = "E"
    NEO6_CINEMA = "F"
    NEO6_MUSIC = "G"
    MULTI_CH_MOVIE_MUSIC = "H"
    CSII_CINEMA = "I"
    CSII_MUSIC = "J"
    CSII_MONO = "K"
    VIRTUAL = "L"
    DTS = "M"
    DTS_NEO6 = "N"
    DDP_PLIIX_MOVIE = "O"
    DDP_PLIIX_MUSIC = "P"
    AAC_PLIIX_MOVIE = "Q"
    AAC_PLIIX_MUSIC = "R"
    AAC = "S"
    SOURCE_DIRECT = "T"
    PURE_DIRECT = "U"
    SACD = "V"
    HEADPHONE = "X"
    DOLBY_DIGITAL_PLUS = "a"
    DOLBY_DIGITAL_PLUS_EX = "b"
    DOLBY_TRUE_HD = "c"
    DOLBY_TRUE_HD_EX = "d"
    DTS_HD_MSTR = "e"
    DTS_HD_HI_RES = "f"
    DTS_HD_EXPRESS = "g"


V2007_SURROUND_NAMES: dict[str, str] = {
    member.value: member.name for member in V2007SurroundCode
}


class V2007THXSet(Enum):
    """Values accepted by `@THX:<value>` set commands."""

    AUTO = "0"
    OFF = "1"
    ON = "2"
    SURR_EX = "3"
    CINEMA = "5"
    GAMES = "6"
    MUSIC = "7"
    SELECT2_CINEMA = "8"
    DTS_NEO6_THX = "9"


V2007_THX_STATUS_NAMES: dict[str, str] = {
    "0": "AUTO",
    "3": "PL2X_MOVIE_THX",
    "4": "PL2_MOVIE_THX",
    "C": "SURR_EX",
    "E": "DTS_ES_THX",
    "F": "NEO6_CINEMA_THX",
    "b": "MUSIC",
    "c": "GAMES",
    "e": "CINEMA",
    "f": "SELECT2_CINEMA",
    "g": "DTS_NEO6_THX",
}


class V2007EQMode(Enum):
    """`@EQM:` values."""

    OFF = "0"
    PRESET_1 = "1"
    FRONT_CURVE = "3"
    FLAT_CURVE = "4"
    AUDYSSEY_CURVE = "5"


class V2007DolbyHeadphone(Enum):
    """`@DHM:` values."""

    BYPASS = "0"
    PLAIN = "1"
    PLII_MOVIE = "2"
    PLII_MUSIC = "3"


class V2007NightMode(Enum):
    """`@NGT:` values."""

    TOGGLE = "0"
    OFF = "1"
    ON = "2"
    AUTO = "3"


class V2007MDAX(Enum):
    """`@MDA:` values."""

    OFF = "1"
    LOW = "2"
    HIGH = "3"


class V2007HDMIChannel(Enum):
    """`@HDM:` values — HDMI output channel."""

    TOGGLE = "0"
    CH1 = "1"
    CH2 = "2"


class V2007HDMIAudioMode(Enum):
    """`@HAM:` values — HDMI audio routing."""

    ENABLE = "1"  # AVR plays audio
    THROUGH = "2"  # passthrough to TV


class V2007IPConverter(Enum):
    """`@IPC:` values — interlace/progressive converter."""

    DISABLE = "1"
    ENABLE = "2"


class V2007Component2(Enum):
    """`@CM2:` values (SR8002 only)."""

    MAIN = "1"
    MULTI = "2"


class V2007TunerMode(Enum):
    """`@TMD:` values.

    Note the set/status overlap on `0`: as a SET command, `0` toggles between
    modes; as a STATUS response, `0` means "no mode selected / not tuned".
    """

    NONE = "0"
    MONO = "1"
    AUTO = "2"
    DIGITAL_AUTO = "3"  # SR8002 HD Radio only


class V2007Menu(Enum):
    """`@MNU:` values."""

    TOGGLE = "0"
    OFF = "1"
    ON = "2"
    ENTER = "3"


class V2007Cursor(Enum):
    """`@CUR:` directional values (ack-only, no status)."""

    UP = "1"
    DOWN = "2"
    LEFT = "3"
    RIGHT = "4"


class V2007InputAD(Enum):
    """`@INP:` values — input analog/digital select status."""

    ANALOG = "1"
    DIGITAL = "2"
    HDMI = "4"
    AUTO_DIGITAL = "6"
    AUTO_HDMI = "8"


class V2007InputSignal(Enum):
    """`@ISG:` values — present input signal type."""

    ANALOG = "1"
    DIGITAL = "2"
    HDMI = "4"


class V2007InputState(Enum):
    """`@IST:` values — input lock state."""

    UNKNOWN = "0"
    OFF = "1"
    ON = "2"


class V2007SignalFormat(Enum):
    """`@SIG:` values — digital signal format."""

    NO_DETECT = "0"
    DD_AC3 = "1"
    DD_AC3_PL = "2"
    DD_SURR_EX = "3"
    DTS = "4"
    DTS_ES_DISCRETE = "5"
    DTS_ES_MATRIX = "6"
    AAC = "7"
    MPEG = "8"
    M_PCM = "9"
    PCM = "A"
    HDCD = "B"
    DSD = "C"
    DTS_96_24 = "D"
    OTHER = "F"
    DD_PLUS = "G"
    DD_TRUE_HD = "H"
    DTS_HD_MSTR = "I"
    DTS_HD_HI_RES = "J"
    DTS_HD_EXPRESS = "K"


class V2007SamplingFrequency(Enum):
    """`@SFQ:` values."""

    OUT_OF_RANGE = "0"
    HZ_32K = "1"
    HZ_44_1K = "2"
    HZ_48K = "3"
    HZ_88_2K = "4"
    HZ_96K = "5"
    HZ_176_4K = "6"
    HZ_192K = "7"
    ANALOG = "F"


class V2007VolumeMode(Enum):
    """`@MVS:` and `@MSS:` — Multi Room volume mode."""

    VARIABLE = "1"
    FIXED = "2"


class V2007StereoMode(Enum):
    """`@MST:` — Multi Room A stereo/mono mode."""

    TOGGLE = "0"
    STEREO = "1"
    MONO = "2"


# Tuner frequency codec — TFQ:0xxxxx where xxxxx is 5 digits.
# See the protocol PDF section 5-1, TFQ:
#   xxxxx <  256        → XM channel (xxxxx = channel)
#   xxxxx <  2000       → AM kHz     (xxxxx = kHz, e.g. 01080 = 1080 kHz)
#   xxxxx >= 2000       → FM 10 kHz units (e.g. 08750 = 87.50 MHz)
class V2007TunerBand(Enum):
    AM = "AM"
    FM = "FM"
    XM = "XM"
