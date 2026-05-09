"""Constants and enums shared across the marantz_rs232 package."""

from enum import Enum

V2015_BAUD_RATE = 9600
V2015_COMMAND_TIMEOUT = 2.0
V2015_MULTI_RESPONSE_DELAY = 0.3
V2015_PROBE_TIMEOUT = 0.8
V2015_CR = b"\r"

V2015_MIN_VOLUME_DB = -80.0
V2015_MAX_VOLUME_DB = 18.0
V2015_VOLUME_DB_RANGE = V2015_MAX_VOLUME_DB - V2015_MIN_VOLUME_DB

_V2015_SINGLE_RESPONSE_PREFIXES = (
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
    "Z2STBY",
    "Z2SLP",
    "Z2CS",
    "Z2HPF",
    "Z3STBY",
    "Z3SLP",
    "Z3CS",
    "Z3HPF",
    "Z4SLP",
)

_V2015_MULTI_RESPONSE_PREFIXES = (
    "CV",
    "PS",
    "Z2",
    "Z3",
    "Z4",
    "Z2CV",
    "Z2PS",
    "Z3CV",
    "Z3PS",
    "VS",
    "TR",
)


class V2015InputSource(Enum):
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


class V2015DigitalInputMode(Enum):
    AUTO = "AUTO"
    HDMI = "HDMI"
    DIGITAL = "DIGITAL"
    ANALOG = "ANALOG"
    EXT_IN = "EXT.IN"
    SEVEN_1_IN = "7.1IN"


class V2015AudioDecodeMode(Enum):
    AUTO = "AUTO"
    PCM = "PCM"
    DTS = "DTS"


class V2015SurroundMode(Enum):
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


class V2015EcoMode(Enum):
    ON = "ON"
    AUTO = "AUTO"
    OFF = "OFF"


class V2015DimmerMode(Enum):
    BRI = "BRI"
    DIM = "DIM"
    DAR = "DAR"
    OFF = "OFF"


class V2015MultEQ(Enum):
    AUDYSSEY = "AUDYSSEY"
    BYP_LR = "BYP.LR"
    FLAT = "FLAT"
    MANUAL = "MANUAL"
    OFF = "OFF"


class V2015DynamicVolume(Enum):
    NGT = "NGT"
    EVE = "EVE"
    DAY = "DAY"
    HEV = "HEV"
    MED = "MED"
    LIT = "LIT"
    OFF = "OFF"


class V2015DRC(Enum):
    AUTO = "AUTO"
    LOW = "LOW"
    MID = "MID"
    HI = "HI"
    OFF = "OFF"


class V2015TunerBand(Enum):
    AM = "AM"
    FM = "FM"


class V2015TunerMode(Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class V2015ZoneChannelMode(Enum):
    STEREO = "ST"
    MONO = "MONO"


class V2015DialogEnhancer(Enum):
    OFF = "OFF"
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class V2015DComp(Enum):
    OFF = "OFF"
    LOW = "LOW"
    MID = "MID"
    HIGH = "HIGH"


class V2015MDAX(Enum):
    OFF = "OFF"
    LOW = "LOW"
    MID = "MID"
    HI = "HI"


class V2015HDMIMonitor(Enum):
    AUTO = "MONIAUTO"
    MONITOR_1 = "MONI1"
    MONITOR_2 = "MONI2"


class V2015HDMIAudioOutput(Enum):
    AMP = "AUDIO AMP"
    TV = "AUDIO TV"


class V2015HDMIResolution(Enum):
    AUTO = "SCAUTO"
    P480 = "SC48P"
    I1080 = "SC10I"
    P720 = "SC72P"
    P1080 = "SC10P"
    P1080_24 = "SC10P24"
    K4 = "SC4K"
    K4_60 = "SC4KF"


class V2015VideoProcessMode(Enum):
    AUTO = "VPMAUTO"
    GAME = "VPMGAME"
    MOVIE = "VPMMOVI"


class V2015AspectMode(Enum):
    NORMAL = "ASPNRM"
    FULL = "ASPFUL"
