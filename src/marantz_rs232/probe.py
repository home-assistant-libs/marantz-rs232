"""Detect which Marantz protocol a receiver speaks."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Union

import serialx

from .const import BAUD_RATE
from .legacy import MarantzLegacyReceiver

if TYPE_CHECKING:
    from .receiver import MarantzReceiver

_LOGGER = logging.getLogger(__name__)


ReceiverClass = Union[type["MarantzReceiver"], type[MarantzLegacyReceiver]]


PROBE_TIMEOUT = 1.5  # generous — legacy spec promises 500 ms; we want both protocols


async def probe(port: str, *, timeout: float = PROBE_TIMEOUT) -> ReceiverClass:
    """Probe `port` and return the receiver class for whichever protocol responds.

    Sends both `@PWR:?\\r` (legacy) and `PW?\\r` (modern) and listens briefly.
    The first byte of the response disambiguates: `@` → legacy, anything else
    (the modern receiver echoes its prefix `P`) → modern.

    Raises `ConnectionError` if neither protocol responds within `timeout`.
    """
    from .receiver import MarantzReceiver  # local to avoid import cycle

    reader, writer = await serialx.open_serial_connection(port, baudrate=BAUD_RATE)
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
            return MarantzLegacyReceiver
        _LOGGER.info("Detected modern protocol on %s (first byte %r)", port, byte)
        return MarantzReceiver
    finally:
        writer.close()
        await writer.wait_closed()
