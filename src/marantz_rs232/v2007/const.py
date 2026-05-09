"""Constants and enums for the v2007 (SR7002-era) Marantz protocol."""

from enum import Enum

V2007_BAUD_RATE = 9600
V2007_COMMAND_TIMEOUT = 1.0  # spec mandates response within 500 ms; 1 s for safety

V2007_PREFIX = "@"
V2007_SEPARATOR = ":"
V2007_TERMINATOR = b"\r"
V2007_MULTI_ROOM_B_SEPARATOR = "="  # SR8002 Multi Room B substitutes `=` for `:`
V2007_HD_RADIO_SEPARATOR = "*"  # SR8002 HD Radio metadata uses `*` separator

# Single-byte ACK / NAK responses framed as `@\x06\r` / `@\x15\r`.
ACK_BYTE = "\x06"
NAK_BYTE = "\x15"


class V2007Model(Enum):
    """Specific Marantz model in the v2007 protocol family.

    GENERIC: assume the documented baseline shared by all listed models.
    SR7002:  baseline; no HD Radio, no Multi Room B, no Component2.
    SR8002:  baseline + HD Radio + Multi Room B + Component2 select.
    """

    GENERIC = "generic"
    SR7002 = "SR7002"
    SR8002 = "SR8002"


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
    """Documented source codes for SR7002/SR8002.

    The wire format is a single character. `@SRC:?` queries return TWO
    characters (video then audio) — see `V2007MainState.source_video` and
    `source_audio`. Setting via `@SRC:<code>` switches both video and audio
    to the same input.
    """

    TV = "1"
    DVD = "2"
    VCR1 = "3"
    DSS_VCR2 = "5"
    AUX1 = "9"
    AUX2 = "A"
    CD_CDR = "C"
    TAPE = "E"
    TUNER1 = "F"
    FM1 = "G"
    AM1 = "H"
    XM1 = "J"


V2007_SOURCE_NAMES: dict[str, str] = {member.value: member.name for member in V2007Source}


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
