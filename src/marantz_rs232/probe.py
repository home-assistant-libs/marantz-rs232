"""Detect which Marantz protocol a receiver speaks."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Union

import serialx

from .v2003 import MarantzV2003Receiver, V2003_BAUD_RATE
from .v2007 import MarantzV2007Receiver
from .v2015 import V2015_BAUD_RATE

if TYPE_CHECKING:
    from .v2015 import MarantzV2015Receiver

_LOGGER = logging.getLogger(__name__)


ReceiverClass = Union[
    type["MarantzV2015Receiver"],
    type[MarantzV2007Receiver],
    type[MarantzV2003Receiver],
]


PROBE_TIMEOUT = 1.5  # generous — both v2007 and v2003 specs promise <= 1 s


async def probe(port: str, *, timeout: float = PROBE_TIMEOUT) -> ReceiverClass:
    """Probe ``port`` and return the receiver class for whichever protocol responds.

    The probe runs in two phases:

    1. **9600 baud, no flow control**. Sends ``@PWR:?\\r`` (v2007) and ``PW?\\r``
       (v2015) back-to-back and waits briefly. If the first response byte is
       ``@`` → v2007; anything else (the v2015 receiver echoes its prefix
       ``P``) → v2015.

    2. **4800 baud with RTS/CTS** (v2003). Only run if phase 1 sees nothing.
       Sends ``@1?A\\r`` (power query for device ID 1) and waits for an
       ``@``-framed response.

    Raises ``ConnectionError`` if no protocol responds within ``timeout``.
    """
    from .v2015 import MarantzV2015Receiver  # local to avoid import cycle

    # Phase 1: v2007 / v2015 at 9600 baud, no hardware flow control.
    reader, writer = await serialx.open_serial_connection(port, baudrate=V2015_BAUD_RATE)
    try:
        writer.write(b"@PWR:?\r")
        writer.write(b"PW?\r")
        await writer.drain()
        try:
            byte = await asyncio.wait_for(reader.readexactly(1), timeout=timeout)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError):
            byte = b""
    finally:
        writer.close()
        await writer.wait_closed()

    if byte == b"@":
        _LOGGER.info("Detected v2007 protocol on %s", port)
        return MarantzV2007Receiver
    if byte:
        _LOGGER.info("Detected v2015 protocol on %s (first byte %r)", port, byte)
        return MarantzV2015Receiver

    # Phase 2: v2003 at 4800 baud with RTS/CTS.
    reader, writer = await serialx.open_serial_connection(
        port, baudrate=V2003_BAUD_RATE, rtscts=True
    )
    try:
        writer.write(b"@1?A\r")
        await writer.drain()
        try:
            byte = await asyncio.wait_for(reader.readexactly(1), timeout=timeout)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
            raise ConnectionError(
                f"No response from receiver on {port} (probed v2007/v2015 at 9600 and v2003 at 4800)"
            ) from err
    finally:
        writer.close()
        await writer.wait_closed()

    if byte == b"@":
        _LOGGER.info("Detected v2003 protocol on %s", port)
        return MarantzV2003Receiver

    raise ConnectionError(
        f"Unrecognized response on {port} at 4800 baud: {byte!r}"
    )
