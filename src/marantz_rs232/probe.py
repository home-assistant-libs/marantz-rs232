"""Detect which Marantz protocol a receiver speaks."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Union

import serialx

from .v2007 import MarantzV2007Receiver
from .v2015 import V2015_BAUD_RATE

if TYPE_CHECKING:
    from .v2015 import MarantzV2015Receiver

_LOGGER = logging.getLogger(__name__)


ReceiverClass = Union[type["MarantzV2015Receiver"], type[MarantzV2007Receiver]]


PROBE_TIMEOUT = 1.5  # generous — legacy spec promises 500 ms; we want both protocols


async def probe(port: str, *, timeout: float = PROBE_TIMEOUT) -> ReceiverClass:
    """Probe `port` and return the receiver class for whichever protocol responds.

    Sends both `@PWR:?\\r` (legacy) and `PW?\\r` (modern) and listens briefly.
    The first byte of the response disambiguates: `@` → legacy, anything else
    (the modern receiver echoes its prefix `P`) → modern.

    Raises `ConnectionError` if neither protocol responds within `timeout`.
    """
    from .v2015 import MarantzV2015Receiver  # local to avoid import cycle

    reader, writer = await serialx.open_serial_connection(port, baudrate=V2015_BAUD_RATE)
    try:
        # Send legacy first; if it answers we're done. Otherwise the modern
        # query goes out next. Both protocols ignore commands they don't
        # recognise, so this is safe in either order.
        writer.write(b"@PWR:?\r")
        writer.write(b"PW?\r")
        await writer.drain()

        try:
            byte = await asyncio.wait_for(reader.readexactly(1), timeout=timeout)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
            raise ConnectionError(
                f"No response from receiver on {port} (probed both protocols)"
            ) from err

        if byte == b"@":
            _LOGGER.info("Detected legacy protocol on %s", port)
            return MarantzV2007Receiver
        _LOGGER.info("Detected modern protocol on %s (first byte %r)", port, byte)
        return MarantzV2015Receiver
    finally:
        writer.close()
        await writer.wait_closed()
