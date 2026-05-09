"""Tests for marantz_rs232 source probing."""

import pytest

from marantz_rs232 import MarantzV2015Receiver, V2015InputSource


async def test_probe_sources(receiver, mock_serial):
    valid_values = {"CD", "DVD", "TUNER", "TV"}

    def handle_command(cmd):
        if cmd.startswith("SI"):
            source_val = cmd[2:]
            if source_val in valid_values:
                mock_serial.inject_response(f"SI{source_val}")

    mock_serial._command_handler = handle_command

    result = await receiver.probe_sources()

    expected = {V2015InputSource(v) for v in valid_values}
    assert result == expected


async def test_probe_sources_restores_original(receiver, mock_serial):
    assert receiver.state.main_zone.input_source == V2015InputSource.CD

    valid_values = {"CD", "DVD"}

    def handle_command(cmd):
        if cmd.startswith("SI"):
            source_val = cmd[2:]
            if source_val in valid_values:
                mock_serial.inject_response(f"SI{source_val}")

    mock_serial._command_handler = handle_command

    await receiver.probe_sources()

    si_commands = [
        d
        for d in mock_serial.written_data
        if d.startswith(b"SI") and not d.endswith(b"?\r")
    ]
    assert si_commands[-1] == b"SICD\r"
    assert receiver.state.main_zone.input_source == V2015InputSource.CD


async def test_probe_includes_current_source(receiver, mock_serial):
    result = await receiver.probe_sources()

    assert V2015InputSource.CD in result


async def test_probe_disconnected_raises():
    recv = MarantzV2015Receiver("/dev/ttyUSB0")
    with pytest.raises(ConnectionError, match="Not connected"):
        await recv.probe_sources()
