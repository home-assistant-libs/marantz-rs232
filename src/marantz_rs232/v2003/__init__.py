"""v2003 (SR9300/SR8300-era) Marantz RS-232 protocol support.

Targets the 2003 lineup that uses the ``@<ID><CODE>\\r`` positional command
framing at 4800 baud with RTS/CTS hardware flow control. Reference:
``docs/Marantz 2003 SR9300 SR8300 RS232C Control Specification v2.00.pdf``.
"""

from .const import (
    V2003_BAUD_RATE,
    V2003_COMMAND_TIMEOUT,
    V2003_PREFIX,
    V2003_SOURCE_NAMES,
    V2003_SUPPORTED_SOURCES,
    V2003_SURROUND_NAMES,
    V2003_TERMINATOR,
    V2003DisplayMode,
    V2003InputMode,
    V2003Model,
    V2003MultiRoomVolumeMode,
    V2003Power,
    V2003SamplingFrequency,
    V2003SignalFormat,
    V2003Source,
    V2003SurroundMode,
    V2003TestTone,
    V2003TestToneMode,
    V2003TunerBand,
    V2003TunerMode,
)
from .players import V2003MainPlayer, V2003MultiRoomPlayer
from .receiver import MarantzV2003Receiver, V2003StateCallback
from .state import V2003MainState, V2003MultiRoomState, V2003ReceiverState

__all__ = [
    "MarantzV2003Receiver",
    "V2003DisplayMode",
    "V2003InputMode",
    "V2003MainPlayer",
    "V2003MainState",
    "V2003Model",
    "V2003MultiRoomPlayer",
    "V2003MultiRoomState",
    "V2003MultiRoomVolumeMode",
    "V2003Power",
    "V2003ReceiverState",
    "V2003SamplingFrequency",
    "V2003SignalFormat",
    "V2003Source",
    "V2003StateCallback",
    "V2003SurroundMode",
    "V2003TestTone",
    "V2003TestToneMode",
    "V2003TunerBand",
    "V2003TunerMode",
    "V2003_BAUD_RATE",
    "V2003_COMMAND_TIMEOUT",
    "V2003_PREFIX",
    "V2003_SOURCE_NAMES",
    "V2003_SUPPORTED_SOURCES",
    "V2003_SURROUND_NAMES",
    "V2003_TERMINATOR",
]
