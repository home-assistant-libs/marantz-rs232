"""Tests for the protocol probe."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import serialx

from marantz_rs232 import (
    MarantzConnectionError,
    MarantzV2007Receiver,
    MarantzV2015Receiver,
    probe,
)


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


async def test_probe_detects_v2007_when_first_byte_is_at_sign() -> None:
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


async def test_probe_error_keeps_api_key_out_of_message() -> None:
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
        with pytest.raises(ConnectionError) as exc_info:
            await probe(
                "esphome://proxy.local:6053/?port_name=RS232&key=SECRET",
                timeout=0.1,
            )

    assert "SECRET" not in str(exc_info.value)


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


@pytest.mark.parametrize("phase", [1, 2])
async def test_probe_serial_exception(phase: int) -> None:
    """A failed open in either baud-rate phase is a connection failure."""
    error = serialx.SerialException("Serial proxy is unavailable")
    reader = asyncio.StreamReader()
    reader.feed_eof()
    writer = MagicMock()
    writer.drain = AsyncMock()
    writer.wait_closed = AsyncMock()
    results = [error] if phase == 1 else [(reader, writer), error]

    with (
        patch(
            "marantz_rs232.probe.serialx.open_serial_connection",
            side_effect=results,
        ) as open_connection,
        pytest.raises(
            MarantzConnectionError, match="Serial proxy is unavailable"
        ) as exc_info,
    ):
        await probe("esphome://proxy.local/?port_name=RS232")

    assert exc_info.value.__cause__ is error
    assert open_connection.await_count == phase
    if phase == 2:
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()
