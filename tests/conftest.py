"""Shared test fixtures for marantz_rs232."""

import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import marantz_rs232
import marantz_rs232.receiver as marantz_receiver
from marantz_rs232 import MarantzReceiver

# Speed up tests by reducing delays
marantz_rs232.COMMAND_TIMEOUT = 0.1
marantz_rs232.MULTI_RESPONSE_DELAY = 0.01
marantz_rs232.PROBE_TIMEOUT = 0.01
marantz_receiver.COMMAND_TIMEOUT = 0.1
marantz_receiver.MULTI_RESPONSE_DELAY = 0.01
marantz_receiver.PROBE_TIMEOUT = 0.01

DEFAULT_QUERY_RESPONSES: dict[str, list[str]] = {
    "PW": ["PWON"],
    "ZM": ["ZMON"],
    "MV": ["MVMAX 98", "MVMIN 99", "MV80"],
    "MU": ["MUOFF"],
    "SI": ["SICD"],
    "MS": ["MSSTEREO"],
    "SD": ["SDAUTO"],
    "DC": ["DCAUTO"],
    "SV": ["SVDVD"],
    "SLP": ["SLPOFF"],
    "ECO": ["ECOOFF"],
    "STBY": ["STBYOFF"],
    "CV": ["CVFL 50", "CVFR 50", "CVC 50", "CVSW 50", "CVSL 50", "CVSR 50"],
    "PS": [
        "PSTONE CTRL OFF",
        "PSBAS 50",
        "PSTRE 50",
        "PSCINEMA EQ.OFF",
        "PSMULTEQ:AUDYSSEY",
        "PSDYNEQ OFF",
        "PSDYNVOL OFF",
        "PSDRC OFF",
        "PSSWR ON",
        "PSLOM OFF",
        "PSDEH OFF",
        "PSHTEQ OFF",
        "PSLFC OFF",
        "PSMDAX OFF",
        "PSDELAY 000",
        "PSNEURAL OFF",
        "PSDCO OFF",
        "PSBSC 00",
        "PSLFE 00",
        "PSREFLEV 0",
        "PSGEQ OFF",
        "PSHEQ OFF",
    ],
    "Z2": ["Z2OFF"],
    "Z3": ["Z3OFF"],
    "Z4": ["Z4OFF"],
    "Z2STBY": ["Z2STBYOFF"],
    "Z2SLP": ["Z2SLPOFF"],
    "Z2CS": ["Z2CSST"],
    "Z2HPF": ["Z2HPFOFF"],
    "Z2CV": ["Z2CVFL 50", "Z2CVFR 50"],
    "Z2PS": ["Z2PSBAS 50", "Z2PSTRE 50"],
    "Z3STBY": ["Z3STBYOFF"],
    "Z3SLP": ["Z3SLPOFF"],
    "Z3CS": ["Z3CSST"],
    "Z3HPF": ["Z3HPFOFF"],
    "Z3CV": ["Z3CVFL 50", "Z3CVFR 50"],
    "Z3PS": ["Z3PSBAS 50", "Z3PSTRE 50"],
    "Z4SLP": ["Z4SLPOFF"],
    "VS": ["VSMONIAUTO", "VSAUDIO AMP"],
    "TR": ["TR1 OFF", "TR2 OFF"],
}


class MockSerialConnection:
    """Mock the serial reader/writer pair with auto-response support."""

    def __init__(self):
        self.reader = asyncio.StreamReader()
        self.writer = MagicMock()
        self.writer.write = MagicMock()
        self.writer.drain = AsyncMock()
        self.writer.close = MagicMock()
        self.writer.wait_closed = AsyncMock()
        self.written_data: list[bytes] = []
        self._query_responses: dict[str, list[str]] = {}
        self._command_handler: Callable[[str], None] | None = None
        self.writer.write.side_effect = self._on_write

    def _on_write(self, data: bytes) -> None:
        self.written_data.append(data)
        cmd = data.decode("ascii").rstrip("\r")
        if cmd.endswith("?"):
            prefix = cmd[:-1]
            for resp in self._query_responses.get(prefix, []):
                self.inject_response(resp)
        elif self._command_handler is not None:
            self._command_handler(cmd)

    def inject_response(self, message: str) -> None:
        self.reader.feed_data(f"{message}\r".encode("ascii"))


@pytest.fixture
async def mock_serial():
    return MockSerialConnection()


@pytest.fixture
async def receiver(mock_serial):
    """Create a connected MarantzReceiver with mocked serial."""
    recv = MarantzReceiver("/dev/ttyUSB0")
    mock_serial._query_responses = dict(DEFAULT_QUERY_RESPONSES)

    async def fake_open(*args, **kwargs):
        return mock_serial.reader, mock_serial.writer

    with patch(
        "marantz_rs232.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        await recv.connect()
        await recv.query_state()

    mock_serial._query_responses.clear()

    yield recv

    if recv.connected:
        await recv.disconnect()


async def connect_with_defaults(mock: MockSerialConnection) -> MarantzReceiver:
    """Helper: connect a receiver with default auto-responses."""
    mock._query_responses = dict(DEFAULT_QUERY_RESPONSES)
    recv = MarantzReceiver("/dev/ttyUSB0")

    async def fake_open(*args, **kwargs):
        return mock.reader, mock.writer

    with patch(
        "marantz_rs232.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        await recv.connect()
        await recv.query_state()

    return recv
