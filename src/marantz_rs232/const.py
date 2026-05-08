"""Constants and enums shared across the marantz_rs232 package."""

from enum import Enum

BAUD_RATE = 9600
COMMAND_TIMEOUT = 2.0
MULTI_RESPONSE_DELAY = 0.3
PROBE_TIMEOUT = 0.8
CR = b"\r"

MIN_VOLUME_DB = -80.0
MAX_VOLUME_DB = 18.0
VOLUME_DB_RANGE = MAX_VOLUME_DB - MIN_VOLUME_DB

_SINGLE_RESPONSE_PREFIXES = (
    "PW",
    "ZM",
    "MV",
    "MU",
    "SI",
    "MS",
    "SD",
    "DC",
    "SV",
    "SLP",
    "ECO",
    "STBY",
)

_MULTI_RESPONSE_PREFIXES = ("CV", "PS", "Z2", "Z3")


class InputSource(Enum):
    PHONO = "PHONO"
    CD = "CD"
    TUNER = "TUNER"
    DVD = "DVD"
    BD = "BD"
    TV = "TV"
    SAT_CBL = "SAT/CBL"
    SAT = "SAT"
    MPLAY = "MPLAY"
    VCR = "VCR"
    GAME = "GAME"
    V_AUX = "V.AUX"
    HDRADIO = "HDRADIO"
    SIRIUS = "SIRIUS"
    SPOTIFY = "SPOTIFY"
    SIRIUSXM = "SIRIUSXM"
    RHAPSODY = "RHAPSODY"
    PANDORA = "PANDORA"
    NAPSTER = "NAPSTER"
    LASTFM = "LASTFM"
    FLICKR = "FLICKR"
    IRADIO = "IRADIO"
    SERVER = "SERVER"
    FAVORITES = "FAVORITES"
    CDR = "CDR"
    AUX1 = "AUX1"
    AUX2 = "AUX2"
    AUX3 = "AUX3"
    AUX4 = "AUX4"
    AUX5 = "AUX5"
    AUX6 = "AUX6"
    AUX7 = "AUX7"
    NET = "NET"
    NET_USB = "NET/USB"
    BT = "BT"
    M_XPORT = "MXPORT"
    USB_IPOD = "USB/IPOD"


class DigitalInputMode(Enum):
    AUTO = "AUTO"
    HDMI = "HDMI"
    DIGITAL = "DIGITAL"
    ANALOG = "ANALOG"
    EXT_IN = "EXT.IN"
    SEVEN_1_IN = "7.1IN"


class AudioDecodeMode(Enum):
    AUTO = "AUTO"
    PCM = "PCM"
    DTS = "DTS"


class SurroundMode(Enum):
    MOVIE = "MOVIE"
    MUSIC = "MUSIC"
    GAME = "GAME"
    DIRECT = "DIRECT"
    PURE_DIRECT = "PURE DIRECT"
    STEREO = "STEREO"
    AUTO = "AUTO"
    NEURAL = "NEURAL"
    STANDARD = "STANDARD"
    DOLBY_DIGITAL = "DOLBY DIGITAL"
    MCH_STEREO = "MCH STEREO"
    MATRIX = "MATRIX"
    VIRTUAL = "VIRTUAL"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    AURO3D = "AURO3D"
    AURO2DSURR = "AURO2DSURR"


class EcoMode(Enum):
    ON = "ON"
    AUTO = "AUTO"
    OFF = "OFF"


class DimmerMode(Enum):
    BRI = "BRI"
    DIM = "DIM"
    DAR = "DAR"
    OFF = "OFF"


class MultEQ(Enum):
    AUDYSSEY = "AUDYSSEY"
    BYP_LR = "BYP.LR"
    FLAT = "FLAT"
    MANUAL = "MANUAL"
    OFF = "OFF"


class DynamicVolume(Enum):
    NGT = "NGT"
    EVE = "EVE"
    DAY = "DAY"
    HEV = "HEV"
    MED = "MED"
    LIT = "LIT"
    OFF = "OFF"


class DRC(Enum):
    AUTO = "AUTO"
    LOW = "LOW"
    MID = "MID"
    HI = "HI"
    OFF = "OFF"


class TunerBand(Enum):
    AM = "AM"
    FM = "FM"


class TunerMode(Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"
