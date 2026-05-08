"""Legacy (SR7002-era) Marantz RS-232 protocol support.

Targets the 2007-2010 Marantz lineup that uses the `@CMD:VALUE\\r` framing:
SR7002, SR8002, SR6003, SR7003, SR8003, SR5004, SR6004, AV7005, AV8003.

Distinct from the 2015 protocol (NR1506/SR5010/etc) implemented at the package
top level. Reference: docs/Marantz 2007 SR7002 SR8002 RS232C Control Specification v1.00.pdf
"""

from .const import (
    LEGACY_BAUD_RATE,
    LEGACY_COMMAND_TIMEOUT,
    SOURCE_NAMES,
    SURROUND_NAMES,
    THX_STATUS_NAMES,
    LegacyComponent2,
    LegacyCursor,
    LegacyDolbyHeadphone,
    LegacyEQMode,
    LegacyHDMIAudioMode,
    LegacyHDMIChannel,
    LegacyInputAD,
    LegacyInputSignal,
    LegacyInputState,
    LegacyIPConverter,
    LegacyMDAX,
    LegacyMenu,
    LegacyModel,
    LegacyNightMode,
    LegacyPower,
    LegacySamplingFrequency,
    LegacySignalFormat,
    LegacySource,
    LegacyStereoMode,
    LegacySurroundCode,
    LegacyTHXSet,
    LegacyTriState,
    LegacyTunerMode,
    LegacyVolumeMode,
    TunerBand,
)
from .players import LegacyMainPlayer, LegacyMultiRoomPlayer
from .receiver import MarantzLegacyReceiver, StateCallback
from .state import LegacyMainState, LegacyMultiRoomState, LegacyReceiverState

__all__ = [
    "LEGACY_BAUD_RATE",
    "LEGACY_COMMAND_TIMEOUT",
    "LegacyComponent2",
    "LegacyCursor",
    "LegacyDolbyHeadphone",
    "LegacyEQMode",
    "LegacyHDMIAudioMode",
    "LegacyHDMIChannel",
    "LegacyIPConverter",
    "LegacyInputAD",
    "LegacyInputSignal",
    "LegacyInputState",
    "LegacyMDAX",
    "LegacyMainPlayer",
    "LegacyMainState",
    "LegacyMenu",
    "LegacyModel",
    "LegacyMultiRoomPlayer",
    "LegacyMultiRoomState",
    "LegacyNightMode",
    "LegacyPower",
    "LegacyReceiverState",
    "LegacySamplingFrequency",
    "LegacySignalFormat",
    "LegacySource",
    "LegacyStereoMode",
    "LegacySurroundCode",
    "LegacyTHXSet",
    "LegacyTriState",
    "LegacyTunerMode",
    "LegacyVolumeMode",
    "MarantzLegacyReceiver",
    "SOURCE_NAMES",
    "SURROUND_NAMES",
    "StateCallback",
    "THX_STATUS_NAMES",
    "TunerBand",
]
