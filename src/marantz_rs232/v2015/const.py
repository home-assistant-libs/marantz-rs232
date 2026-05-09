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
    USB = "USB"
    IPD = "IPD"
    IRP = "IRP"
    FVP = "FVP"
    OTP = "OTP"


class V2015Model(Enum):
    """Marantz model in the v2015 protocol family.

    Source: docs/Marantz 2015 NR_SR_AV IP-232 Protocol.xls. ``GENERIC`` is
    a baseline assuming no model-specific gating.
    """

    GENERIC = "generic"
    AV8802 = "AV8802"
    AV8802A = "AV8802A"
    AV8801 = "AV8801"
    AV7702_MK2 = "AV7702 mkII"
    AV7702 = "AV7702"
    AV7701 = "AV7701"
    AV7005 = "AV7005"
    SR7010 = "SR7010"
    SR7009 = "SR7009"
    SR7008 = "SR7008"
    SR7007 = "SR7007"
    SR7005 = "SR7005"
    SR6010 = "SR6010"
    SR6009 = "SR6009"
    SR6008 = "SR6008"
    SR6007 = "SR6007"
    SR6006 = "SR6006"
    SR6005 = "SR6005"
    SR5010 = "SR5010"
    SR5009 = "SR5009"
    SR5008 = "SR5008"
    SR5007 = "SR5007"
    SR5006 = "SR5006"
    NR1606 = "NR1606"
    NR1605 = "NR1605"
    NR1604 = "NR1604"
    NR1603 = "NR1603"
    NR1602 = "NR1602"
    NR1506 = "NR1506"
    NR1504 = "NR1504"


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


# Per-model `SI` input support — wire codes each model accepts as the input
# source. Source: docs/Marantz 2015 NR_SR_AV IP-232 Protocol.xls.
V2015_SUPPORTED_INPUTS: dict[V2015Model, frozenset[V2015InputSource]] = {
    V2015Model.AV8802: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.AUX3,
        V2015InputSource.AUX4, V2015InputSource.AUX5, V2015InputSource.AUX6,
        V2015InputSource.AUX7, V2015InputSource.BD, V2015InputSource.BT,
        V2015InputSource.CD, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.HDRADIO, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.PHONO, V2015InputSource.SAT_CBL,
        V2015InputSource.SERVER, V2015InputSource.SIRIUSXM, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.AV8801: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.AUX3,
        V2015InputSource.AUX4, V2015InputSource.AUX5, V2015InputSource.AUX6,
        V2015InputSource.AUX7, V2015InputSource.BD, V2015InputSource.CD,
        V2015InputSource.DVD, V2015InputSource.FAVORITES, V2015InputSource.FLICKR,
        V2015InputSource.FVP, V2015InputSource.GAME, V2015InputSource.HDRADIO,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.M_XPORT, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.PHONO, V2015InputSource.SAT_CBL,
        V2015InputSource.SERVER, V2015InputSource.SIRIUSXM, V2015InputSource.SPOTIFY,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
        V2015InputSource.USB_IPOD,
    }),
    V2015Model.AV7702_MK2: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.HDRADIO, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.PHONO, V2015InputSource.SAT_CBL,
        V2015InputSource.SERVER, V2015InputSource.SIRIUSXM, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.AV7702: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FLICKR, V2015InputSource.FVP,
        V2015InputSource.GAME, V2015InputSource.HDRADIO, V2015InputSource.IPD,
        V2015InputSource.IRADIO, V2015InputSource.IRP, V2015InputSource.MPLAY,
        V2015InputSource.NET, V2015InputSource.PANDORA, V2015InputSource.PHONO,
        V2015InputSource.SAT_CBL, V2015InputSource.SERVER, V2015InputSource.SIRIUSXM,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
        V2015InputSource.USB_IPOD,
    }),
    V2015Model.AV7701: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.CD, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.HDRADIO, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.M_XPORT,
        V2015InputSource.NET, V2015InputSource.PANDORA, V2015InputSource.PHONO,
        V2015InputSource.SAT_CBL, V2015InputSource.SERVER, V2015InputSource.SIRIUSXM,
        V2015InputSource.SPOTIFY, V2015InputSource.TUNER, V2015InputSource.TV,
        V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.AV7005: frozenset({
        V2015InputSource.BD, V2015InputSource.CD, V2015InputSource.CDR,
        V2015InputSource.DVD, V2015InputSource.FAVORITES, V2015InputSource.FLICKR,
        V2015InputSource.GAME, V2015InputSource.HDRADIO, V2015InputSource.IPD,
        V2015InputSource.IRADIO, V2015InputSource.M_XPORT, V2015InputSource.NAPSTER,
        V2015InputSource.NET_USB, V2015InputSource.PANDORA, V2015InputSource.PHONO,
        V2015InputSource.RHAPSODY, V2015InputSource.SERVER, V2015InputSource.SIRIUS,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
        V2015InputSource.VCR,
    }),
    V2015Model.SR7010: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.HDRADIO, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.PHONO, V2015InputSource.SAT_CBL,
        V2015InputSource.SERVER, V2015InputSource.SIRIUSXM, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR7009: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FLICKR, V2015InputSource.FVP,
        V2015InputSource.GAME, V2015InputSource.HDRADIO, V2015InputSource.IPD,
        V2015InputSource.IRADIO, V2015InputSource.IRP, V2015InputSource.MPLAY,
        V2015InputSource.NET, V2015InputSource.PANDORA, V2015InputSource.PHONO,
        V2015InputSource.SAT_CBL, V2015InputSource.SERVER, V2015InputSource.SIRIUSXM,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
        V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR7008: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.CD, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.HDRADIO, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.M_XPORT,
        V2015InputSource.NET, V2015InputSource.PANDORA, V2015InputSource.PHONO,
        V2015InputSource.SAT_CBL, V2015InputSource.SERVER, V2015InputSource.SIRIUSXM,
        V2015InputSource.SPOTIFY, V2015InputSource.TUNER, V2015InputSource.TV,
        V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR7007: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.CD, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.HDRADIO, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.M_XPORT,
        V2015InputSource.NET, V2015InputSource.PANDORA, V2015InputSource.PHONO,
        V2015InputSource.SAT_CBL, V2015InputSource.SERVER, V2015InputSource.SIRIUSXM,
        V2015InputSource.SPOTIFY, V2015InputSource.TUNER, V2015InputSource.TV,
        V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR7005: frozenset({
        V2015InputSource.BD, V2015InputSource.CD, V2015InputSource.CDR,
        V2015InputSource.DVD, V2015InputSource.FAVORITES, V2015InputSource.FLICKR,
        V2015InputSource.GAME, V2015InputSource.HDRADIO, V2015InputSource.IPD,
        V2015InputSource.IRADIO, V2015InputSource.M_XPORT, V2015InputSource.NAPSTER,
        V2015InputSource.NET, V2015InputSource.NET_USB, V2015InputSource.PANDORA,
        V2015InputSource.PHONO, V2015InputSource.RHAPSODY, V2015InputSource.SERVER,
        V2015InputSource.SIRIUS, V2015InputSource.SPOTIFY, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB, V2015InputSource.VCR,
    }),
    V2015Model.SR6010: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.NET, V2015InputSource.PANDORA,
        V2015InputSource.PHONO, V2015InputSource.SAT_CBL, V2015InputSource.SERVER,
        V2015InputSource.SIRIUSXM, V2015InputSource.TUNER, V2015InputSource.TV,
        V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR6009: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FLICKR, V2015InputSource.FVP,
        V2015InputSource.GAME, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.PHONO, V2015InputSource.SAT_CBL,
        V2015InputSource.SERVER, V2015InputSource.SIRIUSXM, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR6008: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.CD, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.M_XPORT, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.PHONO, V2015InputSource.SAT_CBL,
        V2015InputSource.SERVER, V2015InputSource.SIRIUSXM, V2015InputSource.SPOTIFY,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
        V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR6007: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.CD, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.M_XPORT, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.PHONO, V2015InputSource.SAT_CBL,
        V2015InputSource.SERVER, V2015InputSource.SIRIUSXM, V2015InputSource.SPOTIFY,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
        V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR6006: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.CD, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.HDRADIO, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.M_XPORT, V2015InputSource.NAPSTER,
        V2015InputSource.NET_USB, V2015InputSource.OTP, V2015InputSource.PANDORA,
        V2015InputSource.PHONO, V2015InputSource.RHAPSODY, V2015InputSource.SAT,
        V2015InputSource.SERVER, V2015InputSource.TUNER, V2015InputSource.TV,
        V2015InputSource.USB, V2015InputSource.VCR,
    }),
    V2015Model.SR6005: frozenset({
        V2015InputSource.BD, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.GAME, V2015InputSource.HDRADIO, V2015InputSource.IPD,
        V2015InputSource.M_XPORT, V2015InputSource.SIRIUS, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB, V2015InputSource.VCR,
    }),
    V2015Model.SR5010: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.NET, V2015InputSource.PANDORA,
        V2015InputSource.SAT_CBL, V2015InputSource.SERVER, V2015InputSource.SIRIUSXM,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
        V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR5009: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FLICKR, V2015InputSource.FVP,
        V2015InputSource.GAME, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.SAT_CBL, V2015InputSource.SERVER,
        V2015InputSource.SIRIUSXM, V2015InputSource.TUNER, V2015InputSource.TV,
        V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR5008: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.CD, V2015InputSource.CDR, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FLICKR, V2015InputSource.FVP,
        V2015InputSource.GAME, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.M_XPORT,
        V2015InputSource.NET, V2015InputSource.PANDORA, V2015InputSource.SAT_CBL,
        V2015InputSource.SERVER, V2015InputSource.SIRIUSXM, V2015InputSource.SPOTIFY,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
        V2015InputSource.USB_IPOD,
    }),
    V2015Model.SR5007: frozenset({
        V2015InputSource.AUX1, V2015InputSource.BD, V2015InputSource.CD,
        V2015InputSource.CDR, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.M_XPORT, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.SAT_CBL, V2015InputSource.SERVER,
        V2015InputSource.SIRIUSXM, V2015InputSource.SPOTIFY, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB,
    }),
    V2015Model.SR5006: frozenset({
        V2015InputSource.AUX1, V2015InputSource.BD, V2015InputSource.CD,
        V2015InputSource.CDR, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.M_XPORT, V2015InputSource.NAPSTER, V2015InputSource.NET_USB,
        V2015InputSource.OTP, V2015InputSource.PANDORA, V2015InputSource.RHAPSODY,
        V2015InputSource.SAT, V2015InputSource.SERVER, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB, V2015InputSource.VCR,
    }),
    V2015Model.NR1606: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.NET, V2015InputSource.PANDORA,
        V2015InputSource.SAT_CBL, V2015InputSource.SERVER, V2015InputSource.SIRIUSXM,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
        V2015InputSource.USB_IPOD,
    }),
    V2015Model.NR1605: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.BT, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FLICKR, V2015InputSource.FVP,
        V2015InputSource.GAME, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.MPLAY, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.SAT_CBL, V2015InputSource.SERVER,
        V2015InputSource.SIRIUSXM, V2015InputSource.TUNER, V2015InputSource.TV,
        V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.NR1604: frozenset({
        V2015InputSource.AUX1, V2015InputSource.AUX2, V2015InputSource.BD,
        V2015InputSource.CD, V2015InputSource.DVD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.M_XPORT, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.SAT_CBL, V2015InputSource.SERVER,
        V2015InputSource.SIRIUSXM, V2015InputSource.SPOTIFY, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.NR1603: frozenset({
        V2015InputSource.AUX1, V2015InputSource.BD, V2015InputSource.CD,
        V2015InputSource.DVD, V2015InputSource.FAVORITES, V2015InputSource.FLICKR,
        V2015InputSource.FVP, V2015InputSource.GAME, V2015InputSource.IPD,
        V2015InputSource.IRADIO, V2015InputSource.IRP, V2015InputSource.MPLAY,
        V2015InputSource.M_XPORT, V2015InputSource.NET, V2015InputSource.PANDORA,
        V2015InputSource.SAT_CBL, V2015InputSource.SERVER, V2015InputSource.SIRIUSXM,
        V2015InputSource.SPOTIFY, V2015InputSource.TUNER, V2015InputSource.TV,
        V2015InputSource.USB,
    }),
    V2015Model.NR1602: frozenset({
        V2015InputSource.BD, V2015InputSource.CD, V2015InputSource.DVD,
        V2015InputSource.FAVORITES, V2015InputSource.FLICKR, V2015InputSource.FVP,
        V2015InputSource.GAME, V2015InputSource.IPD, V2015InputSource.IRADIO,
        V2015InputSource.IRP, V2015InputSource.M_XPORT, V2015InputSource.NAPSTER,
        V2015InputSource.NET_USB, V2015InputSource.OTP, V2015InputSource.PANDORA,
        V2015InputSource.RHAPSODY, V2015InputSource.SAT, V2015InputSource.SERVER,
        V2015InputSource.TUNER, V2015InputSource.TV, V2015InputSource.USB,
    }),
    V2015Model.NR1506: frozenset({
        V2015InputSource.AUX1, V2015InputSource.BT, V2015InputSource.CD,
        V2015InputSource.FAVORITES, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.NET, V2015InputSource.PANDORA,
        V2015InputSource.SAT_CBL, V2015InputSource.SERVER, V2015InputSource.SIRIUSXM,
        V2015InputSource.SPOTIFY, V2015InputSource.TUNER, V2015InputSource.TV,
        V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
    V2015Model.NR1504: frozenset({
        V2015InputSource.AUX1, V2015InputSource.CD, V2015InputSource.FAVORITES,
        V2015InputSource.FLICKR, V2015InputSource.FVP, V2015InputSource.GAME,
        V2015InputSource.IPD, V2015InputSource.IRADIO, V2015InputSource.IRP,
        V2015InputSource.MPLAY, V2015InputSource.M_XPORT, V2015InputSource.NET,
        V2015InputSource.PANDORA, V2015InputSource.SAT_CBL, V2015InputSource.SERVER,
        V2015InputSource.SIRIUSXM, V2015InputSource.SPOTIFY, V2015InputSource.TUNER,
        V2015InputSource.TV, V2015InputSource.USB, V2015InputSource.USB_IPOD,
    }),
}
# AV8802 and AV8802A share a column in the spec.
V2015_SUPPORTED_INPUTS[V2015Model.AV8802A] = V2015_SUPPORTED_INPUTS[V2015Model.AV8802]
# GENERIC accepts any documented input.
V2015_SUPPORTED_INPUTS[V2015Model.GENERIC] = frozenset(V2015InputSource)
