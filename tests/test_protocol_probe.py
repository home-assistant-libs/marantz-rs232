"""Tests for the protocol probe."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from marantz_rs232 import MarantzV2007Receiver, MarantzV2015Receiver, probe


async def _run_probe_with_first_byte(first_byte: bytes) -> type:
    """Helper: run probe() with a mock that emits `first_byte` as the first response byte."""
    reader = asyncio.StreamReader()
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    async def fake_open(*_a, **_kw):
        return reader, writer

    reader.feed_data(first_byte)
    with patch(
        "marantz_rs232.probe.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        return await probe("/dev/ttyUSB0", timeout=0.5)


async def test_probe_detects_legacy_when_first_byte_is_at_sign() -> None:
    cls = await _run_probe_with_first_byte(b"@PWR:2\r")
    assert cls is MarantzV2007Receiver


async def test_probe_detects_modern_when_first_byte_is_p() -> None:
    cls = await _run_probe_with_first_byte(b"PWON\r")
    assert cls is MarantzV2015Receiver


async def test_probe_raises_on_silent_port() -> None:
    reader = asyncio.StreamReader()
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    async def fake_open(*_a, **_kw):
        return reader, writer

    with patch(
        "marantz_rs232.probe.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        with pytest.raises(ConnectionError):
            await probe("/dev/ttyUSB0", timeout=0.1)


async def test_probe_sends_both_protocol_queries() -> None:
    """Both queries must be sent so whichever protocol is on the wire can answer."""
    reader = asyncio.StreamReader()
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    async def fake_open(*_a, **_kw):
        return reader, writer

    reader.feed_data(b"@PWR:2\r")
    with patch(
        "marantz_rs232.probe.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        await probe("/dev/ttyUSB0", timeout=0.5)

    written_bytes = b"".join(call.args[0] for call in writer.write.call_args_list)
    assert b"@PWR:?\r" in written_bytes
    assert b"PW?\r" in written_bytes
