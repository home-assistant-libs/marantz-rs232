"""Legacy (SR7002-era) Marantz RS-232 protocol support.

Targets the 2007-2010 Marantz lineup that uses the `@CMD:VALUE\\r` framing:
SR7002, SR8002, SR6003, SR7003, SR8003, SR5004, SR6004, AV7005, AV8003.

Distinct from the 2015 protocol (NR1506/SR5010/etc) implemented at the package
top level. Reference: docs/Marantz 2007 SR7002 SR8002 RS232C Control Specification v1.00.pdf
"""

from .const import (
    V2007_BAUD_RATE,
    V2007_COMMAND_TIMEOUT,
    V2007_SOURCE_NAMES,
    V2007_SURROUND_NAMES,
    V2007_THX_STATUS_NAMES,
    V2007Component2,
    V2007Cursor,
    V2007DolbyHeadphone,
    V2007EQMode,
    V2007HDMIAudioMode,
    V2007HDMIChannel,
    V2007InputAD,
    V2007InputSignal,
    V2007InputState,
    V2007IPConverter,
    V2007MDAX,
    V2007Menu,
    V2007Model,
    V2007NightMode,
    V2007Power,
    V2007SamplingFrequency,
    V2007SignalFormat,
    V2007Source,
    V2007StereoMode,
    V2007SurroundCode,
    V2007THXSet,
    V2007TriState,
    V2007TunerMode,
    V2007VolumeMode,
    V2007TunerBand,
)
from .players import V2007MainPlayer, V2007MultiRoomPlayer
from .receiver import MarantzV2007Receiver, V2007StateCallback
from .state import V2007MainState, V2007MultiRoomState, V2007ReceiverState

__all__ = [
    "V2007_BAUD_RATE",
    "V2007_COMMAND_TIMEOUT",
    "V2007Component2",
    "V2007Cursor",
    "V2007DolbyHeadphone",
    "V2007EQMode",
    "V2007HDMIAudioMode",
    "V2007HDMIChannel",
    "V2007IPConverter",
    "V2007InputAD",
    "V2007InputSignal",
    "V2007InputState",
    "V2007MDAX",
    "V2007MainPlayer",
    "V2007MainState",
    "V2007Menu",
    "V2007Model",
    "V2007MultiRoomPlayer",
    "V2007MultiRoomState",
    "V2007NightMode",
    "V2007Power",
    "V2007ReceiverState",
    "V2007SamplingFrequency",
    "V2007SignalFormat",
    "V2007Source",
    "V2007StereoMode",
    "V2007SurroundCode",
    "V2007THXSet",
    "V2007TriState",
    "V2007TunerMode",
    "V2007VolumeMode",
    "MarantzV2007Receiver",
    "V2007_SOURCE_NAMES",
    "V2007_SURROUND_NAMES",
    "V2007StateCallback",
    "V2007_THX_STATUS_NAMES",
    "V2007TunerBand",
]
