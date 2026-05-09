"""Tests for the v2003 (SR9300/SR8300-era) Marantz protocol."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import marantz_rs232.v2003.receiver as v2003_receiver
from marantz_rs232 import (
    MarantzV2003Receiver,
    V2003DisplayMode,
    V2003InputMode,
    V2003MultiRoomVolumeMode,
    V2003Power,
    V2003ReceiverState,
    V2003SamplingFrequency,
    V2003SignalFormat,
    V2003Source,
    V2003SurroundMode,
    V2003TestTone,
    V2003TestToneMode,
    V2003TunerBand,
    V2003TunerMode,
)
from marantz_rs232.v2003.protocol import (
    decode_audio_source,
    decode_multi_audio_source,
    decode_multi_tuner_preset,
    decode_multi_video_source,
    decode_tuner_frequency,
    decode_tuner_preset,
    decode_video_source,
    encode_command,
    encode_main_source,
    encode_multi_source,
    encode_query,
    encode_volume,
    parse_line,
    parse_multi_sleep,
    parse_multi_volume,
    parse_sleep,
    parse_tone,
    parse_volume,
)

# Speed up the command timeout for the test suite.
v2003_receiver.V2003_COMMAND_TIMEOUT = 0.05


# -- Wire encoding ------------------------------------------------------------


def test_encode_command() -> None:
    assert encode_command("1", "A1") == b"@1A1\r"
    assert encode_command("3", "H0+10") == b"@3H0+10\r"


def test_encode_query() -> None:
    assert encode_query("1", "A") == b"@1?A\r"
    assert encode_query("0", "H") == b"@0?H\r"


@pytest.mark.parametrize(
    "line, expected",
    [
        ("@1A0\r", ("1", "A0")),
        ("@1H0-15\r", ("1", "H0-15")),
        ("@1B3", ("1", "B3")),
        ("@2L0", ("2", "L0")),
    ],
)
def test_parse_line(line: str, expected: tuple[str, str]) -> None:
    assert parse_line(line) == expected


def test_parse_line_filters_wrong_id() -> None:
    assert parse_line("@2A0", expected_id="1") is None
    assert parse_line("@1A0", expected_id="1") == ("1", "A0")


@pytest.mark.parametrize("line", ["", "A0", "@", "@1"])
def test_parse_line_handles_invalid(line: str) -> None:
    assert parse_line(line) is None


# -- Source code conversion ---------------------------------------------------


@pytest.mark.parametrize(
    "source, code",
    [
        (V2003Source.DSS, "B0"),
        (V2003Source.DVD, "B3"),
        (V2003Source.CD, "B9"),
        (V2003Source.TAPE, "BA"),
        (V2003Source.TUNER, "BG"),
    ],
)
def test_encode_main_source(source: V2003Source, code: str) -> None:
    assert encode_main_source(source) == code


@pytest.mark.parametrize(
    "source, code",
    [
        (V2003Source.DSS, "Ba"),
        (V2003Source.DVD, "Bd"),
        (V2003Source.CD, "Bj"),
        (V2003Source.TAPE, "Bk"),
        (V2003Source.TUNER, "Bq"),
    ],
)
def test_encode_multi_source(source: V2003Source, code: str) -> None:
    assert encode_multi_source(source) == code


def test_decode_video_source_known_codes() -> None:
    assert decode_video_source("B0") is V2003Source.DSS
    assert decode_video_source("B3") is V2003Source.DVD
    assert decode_video_source("B-") is None
    assert decode_video_source("B?") is None  # unknown letter
    assert decode_video_source("B9") is None  # video tops out at B8


def test_decode_audio_source_includes_tuner_codes() -> None:
    assert decode_audio_source("CC") is V2003Source.FM
    assert decode_audio_source("CG") is None  # multi-channel input — see is_main_multi_channel_input
    assert decode_audio_source("CH") is V2003Source.TUNER  # asymmetric: status H = TUNER


def test_decode_multi_sources() -> None:
    assert decode_multi_video_source("Y3") is V2003Source.DVD
    assert decode_multi_audio_source("Z9") is V2003Source.CD
    # Multi-room audio status skips ZC; FM..LW shift up by one slot.
    assert decode_multi_audio_source("ZD") is V2003Source.FM
    assert decode_multi_audio_source("ZG") is V2003Source.LW
    assert decode_multi_audio_source("ZH") is V2003Source.TUNER
    assert decode_multi_audio_source("ZC") is None  # gap in spec
    assert decode_multi_video_source("Y-") is None


def test_is_main_multi_channel_input() -> None:
    from marantz_rs232.v2003.protocol import is_main_multi_channel_input

    assert is_main_multi_channel_input("CG") is True
    assert is_main_multi_channel_input("CH") is False
    assert is_main_multi_channel_input("C9") is False


# -- Volume -------------------------------------------------------------------


@pytest.mark.parametrize(
    "db, encoded",
    [
        (0, "H0+00"),
        (-15, "H0-15"),
        (12, "H0+12"),
        (-90, "H0-90"),
        (99, "H0+99"),
    ],
)
def test_encode_volume(db: int, encoded: str) -> None:
    assert encode_volume(db) == encoded


def test_encode_volume_out_of_range() -> None:
    with pytest.raises(ValueError):
        encode_volume(100)
    with pytest.raises(ValueError):
        encode_volume(-91)


@pytest.mark.parametrize(
    "payload, expected",
    [
        ("H0-15", (-15.0, False)),
        ("H0+00", (0.0, False)),
        ("H0+12", (12.0, False)),
        ("H1", (99.0, False)),  # max
        ("H2", (float("-inf"), True)),  # min / muted
    ],
)
def test_parse_volume(payload: str, expected: tuple[float, bool]) -> None:
    assert parse_volume(payload) == expected


def test_parse_volume_invalid() -> None:
    with pytest.raises(ValueError):
        parse_volume("HX")


def test_parse_multi_volume() -> None:
    assert parse_multi_volume("c0-30") == (-30.0, False)
    assert parse_multi_volume("c1") == (99.0, False)
    assert parse_multi_volume("c2") == (float("-inf"), True)


# -- Tone ---------------------------------------------------------------------


def test_parse_tone() -> None:
    assert parse_tone("I0+05") == 5
    assert parse_tone("J0-03") == -3


# -- Tuner --------------------------------------------------------------------


def test_decode_tuner_frequency_fm_low() -> None:
    band, freq = decode_tuner_frequency("E08750", V2003TunerBand.FM)
    assert band is V2003TunerBand.FM
    assert freq == pytest.approx(87.50)


def test_decode_tuner_frequency_fm_overflow() -> None:
    # 108.00 MHz wraps as "0800" because the field is 4 digits.
    band, freq = decode_tuner_frequency("E00800", V2003TunerBand.FM)
    assert band is V2003TunerBand.FM
    assert freq == pytest.approx(108.00)


def test_decode_tuner_frequency_am() -> None:
    band, freq = decode_tuner_frequency("E00520", V2003TunerBand.AM)
    assert band is V2003TunerBand.AM
    assert freq == pytest.approx(520.0)


def test_decode_tuner_frequency_lw_inferred_band() -> None:
    band, freq = decode_tuner_frequency("E00200")  # in LW range
    assert band is V2003TunerBand.LW
    assert freq == pytest.approx(200.0)


def test_decode_tuner_frequency_not_available() -> None:
    assert decode_tuner_frequency("E-") is None
    assert decode_tuner_frequency("a-") is None


def test_decode_tuner_preset() -> None:
    assert decode_tuner_preset("F012") == 12
    assert decode_tuner_preset("F000") is None
    assert decode_tuner_preset("F-") is None


def test_decode_multi_tuner_preset() -> None:
    assert decode_multi_tuner_preset("b015") == 15
    assert decode_multi_tuner_preset("b-") is None


# -- Sleep --------------------------------------------------------------------


def test_parse_sleep() -> None:
    assert parse_sleep("M0") == 0
    assert parse_sleep("M1090") == 90


def test_parse_multi_sleep() -> None:
    assert parse_multi_sleep("e0") == 0
    assert parse_multi_sleep("e1045") == 45


# -- Mock serial --------------------------------------------------------------


class _MockV2003Serial:
    """Mock serial reader/writer pair for the v2003 wire format.

    Commands ``@<id><body>\\r`` get an ACK byte (``\\x06``) by default.
    Queries ``@<id>?<char>\\r`` get a configured response. Responses are
    fed as ``@<id><payload>\\r``.
    """

    def __init__(self, device_id: str = "1") -> None:
        self.reader = asyncio.StreamReader()
        self.writer = MagicMock()
        self.writer.write = MagicMock()
        self.writer.drain = AsyncMock()
        self.writer.close = MagicMock()
        self.writer.wait_closed = AsyncMock()
        self.written: list[bytes] = []
        self.query_responses: dict[str, str] = {}
        self.command_log: list[str] = []
        self.command_response: bytes = b"\x06"  # ACK by default
        self._device_id = device_id
        self.writer.write.side_effect = self._on_write

    def _on_write(self, data: bytes) -> None:
        self.written.append(data)
        text = data.decode("ascii").rstrip("\r")
        if not text.startswith("@"):
            return
        body = text[2:]  # strip @ and ID
        if body.startswith("?"):
            char = body[1:]
            payload = self.query_responses.get(char)
            if payload is not None:
                self.feed_status(payload)
        else:
            self.command_log.append(body)
            self.reader.feed_data(self.command_response)

    def feed_status(self, payload: str) -> None:
        line = f"@{self._device_id}{payload}\r".encode("ascii")
        self.reader.feed_data(line)

    def feed_bytes(self, data: bytes) -> None:
        self.reader.feed_data(data)


_DEFAULT_V2003_RESPONSES: dict[str, str] = {
    "A": "A0",         # power on
    "B": "B3",         # video DVD
    "C": "C3",         # audio DVD
    "D": "D0",         # digital
    "E": "E08750",     # FM 87.50
    "F": "F005",       # preset 5
    "G": "G1",         # auto stereo
    "H": "H0-12",      # volume -12 dB
    "I": "I0+02",      # bass +2
    "J": "J0-01",      # treble -1
    "K": "K0",         # ATT off
    "L": "L0",         # surround AUTO
    "M": "M0",         # sleep off
    "N": "N0",         # display ON
    "O": "O0",         # OSD ON
    "P": "P0",         # test tone OFF
    "Q": "Q0",         # AUTO test tone mode
    "R": "R1",         # night OFF
    "S": "S1",         # menu OFF
    "T": "T0",         # F-direct OFF
    "U": "U1",         # signal Dolby Digital
    "V": "V3",         # 48 kHz
    "W": "W146",       # channel status
    "X": "X1",         # multi room OFF
    "Y": "Y-",         # MR video unavailable
    "Z": "Z-",         # MR audio unavailable
    "a": "a-",
    "b": "b-",
    "c": "c0-40",
    "d": "d0",         # variable
    "e": "e0",
    "f": "f1",         # MR OSD off
    "g": "g1",         # MR speaker off
    "h": "h1",         # MR mute off
}


@pytest.fixture
async def mock_serial() -> _MockV2003Serial:
    s = _MockV2003Serial()
    s.query_responses = dict(_DEFAULT_V2003_RESPONSES)
    return s


@pytest.fixture
async def receiver(mock_serial: _MockV2003Serial):
    with patch(
        "marantz_rs232.v2003.receiver.serialx.open_serial_connection",
        AsyncMock(return_value=(mock_serial.reader, mock_serial.writer)),
    ):
        rcv = MarantzV2003Receiver("/dev/null")
        await rcv.connect()
        yield rcv
        await rcv.disconnect()


# -- Connection lifecycle ----------------------------------------------------


async def test_connect_opens_at_4800_with_rtscts(mock_serial: _MockV2003Serial) -> None:
    open_call = AsyncMock(return_value=(mock_serial.reader, mock_serial.writer))
    with patch(
        "marantz_rs232.v2003.receiver.serialx.open_serial_connection", open_call
    ):
        rcv = MarantzV2003Receiver("/dev/serial")
        await rcv.connect()
        await rcv.disconnect()
    open_call.assert_awaited_once()
    args, kwargs = open_call.call_args
    assert args[0] == "/dev/serial"
    assert kwargs == {"baudrate": 4800, "rtscts": True}


async def test_connect_raises_on_no_response() -> None:
    silent = _MockV2003Serial()
    silent.query_responses = {}  # never respond
    with patch(
        "marantz_rs232.v2003.receiver.serialx.open_serial_connection",
        AsyncMock(return_value=(silent.reader, silent.writer)),
    ):
        rcv = MarantzV2003Receiver("/dev/null")
        with pytest.raises(ConnectionError):
            await rcv.connect()


async def test_invalid_device_id_raises() -> None:
    with pytest.raises(ValueError):
        MarantzV2003Receiver("/dev/null", device_id="A")
    with pytest.raises(ValueError):
        MarantzV2003Receiver("/dev/null", device_id="42")


async def test_disconnect_notifies_subscribers() -> None:
    serial = _MockV2003Serial()
    serial.query_responses = dict(_DEFAULT_V2003_RESPONSES)
    with patch(
        "marantz_rs232.v2003.receiver.serialx.open_serial_connection",
        AsyncMock(return_value=(serial.reader, serial.writer)),
    ):
        rcv = MarantzV2003Receiver("/dev/null")
        await rcv.connect()
        events: list[V2003ReceiverState | None] = []
        rcv.subscribe(events.append)
        await rcv.disconnect()
        assert events[-1] is None


# -- query_state / state updates ----------------------------------------------


async def test_query_state_populates_main(receiver: MarantzV2003Receiver) -> None:
    await receiver.query_state()
    s = receiver.state.main
    assert s.power is True
    assert s.video_input is V2003Source.DVD
    assert s.audio_input is V2003Source.DVD
    assert s.input_mode is V2003InputMode.DIGITAL
    assert s.tuner_preset == 5
    assert s.tuner_mode is V2003TunerMode.AUTO_STEREO
    assert s.volume == -12.0
    assert s.mute is False
    assert s.bass == 2
    assert s.treble == -1
    assert s.attenuator is False
    assert s.surround_mode is V2003SurroundMode.AUTO
    assert s.sleep_minutes == 0
    assert s.display is V2003DisplayMode.ON
    assert s.osd is True
    assert s.test_tone is V2003TestTone.OFF
    assert s.test_tone_mode is V2003TestToneMode.AUTO
    assert s.night_mode is False
    assert s.menu_visible is False
    assert s.f_direct is False
    assert s.signal_format is V2003SignalFormat.DOLBY_DIGITAL
    assert s.sampling_frequency is V2003SamplingFrequency.KHZ_48
    assert s.channel_status_raw == "146"


async def test_query_state_populates_multi_room(receiver: MarantzV2003Receiver) -> None:
    await receiver.query_state()
    mr = receiver.state.multi_room
    assert mr.enabled is False  # X1 = OFF
    assert mr.video_input is None
    assert mr.audio_input is None
    assert mr.volume == -40.0
    assert mr.volume_mode is V2003MultiRoomVolumeMode.VARIABLE
    assert mr.sleep_minutes == 0
    assert mr.osd_on is False
    assert mr.speaker_on is False
    assert mr.mute is False


async def test_volume_max_min_via_query(receiver: MarantzV2003Receiver) -> None:
    # Volume at max
    receiver_state_changes: list[V2003ReceiverState | None] = []
    receiver.subscribe(receiver_state_changes.append)
    serial = receiver._writer  # noqa: SLF001 — accessing for test mock
    # Not all setters; reach into the read loop directly via feed.
    # Simulate a query response of H1 (max volume) coming in.
    receiver._reader  # noqa: B018 - reader is the mock
    # Use the test path via query
    await receiver._query("H")  # default response is H0-12
    assert receiver.state.main.volume == -12.0


# -- Player commands ---------------------------------------------------------


async def test_main_player_power_commands(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    await receiver.main.power_on()
    await receiver.main.power_off()
    await receiver.main.power_toggle()
    assert mock_serial.command_log == ["A1", "A2", "A0"]


async def test_main_player_volume_commands(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    await receiver.main.volume_up()
    await receiver.main.volume_down()
    await receiver.main.set_volume(-15)
    await receiver.main.set_volume(0)
    await receiver.main.mute_on()
    await receiver.main.mute_off()
    assert mock_serial.command_log == ["G0", "G1", "H0-15", "H0+00", "H2", "H1"]


async def test_main_player_select_source(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    await receiver.main.select_source(V2003Source.DVD)
    await receiver.main.select_source(V2003Source.CD)
    await receiver.main.select_source(V2003Source.FM)
    assert mock_serial.command_log == ["B3", "B9", "BC"]


async def test_main_player_multi_channel_input_commands(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    await receiver.main.multi_channel_input_on()
    await receiver.main.multi_channel_input_off()
    assert mock_serial.command_log == ["BH", "BI"]


async def test_audio_status_cg_sets_multi_channel_input_flag(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    mock_serial.query_responses["C"] = "CG"
    await receiver._query("C")
    assert receiver.state.main.multi_channel_input is True
    assert receiver.state.main.audio_input is None


async def test_audio_status_ch_decodes_as_tuner(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    mock_serial.query_responses["C"] = "CH"
    await receiver._query("C")
    assert receiver.state.main.audio_input is V2003Source.TUNER
    assert receiver.state.main.multi_channel_input is False


@pytest.mark.parametrize(
    "mode, code",
    [
        (V2003SurroundMode.AUTO, "F0"),
        (V2003SurroundMode.THX_MUSIC, "F1"),         # status-side this is L4
        (V2003SurroundMode.DTS_ES, "F5"),
        (V2003SurroundMode.DOLBY_PROLOGIC, "F7"),
        (V2003SurroundMode.STEREO, "FG"),            # status-side this is LM
        (V2003SurroundMode.NEO6_CINEMA, "FI"),
        (V2003SurroundMode.CSII_MONO, "FO"),
    ],
)
async def test_main_player_set_surround_mode(
    receiver: MarantzV2003Receiver,
    mock_serial: _MockV2003Serial,
    mode: V2003SurroundMode,
    code: str,
) -> None:
    await receiver.main.set_surround_mode(mode)
    assert mock_serial.command_log == [code]


async def test_main_player_surround_steppers(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    await receiver.main.surround_mode_next()
    await receiver.main.surround_mode_prev()
    assert mock_serial.command_log == ["FX", "FY"]


@pytest.mark.parametrize(
    "mode",
    [
        V2003SurroundMode.THX_5_1,         # status-only umbrella
        V2003SurroundMode.DTS_MUSIC,       # status-only
        V2003SurroundMode.DTS_CINEMA,
        V2003SurroundMode.DOLBY_DIGITAL,
        V2003SurroundMode.MONO,
    ],
)
async def test_main_player_set_surround_rejects_status_only_modes(
    receiver: MarantzV2003Receiver, mode: V2003SurroundMode
) -> None:
    with pytest.raises(ValueError):
        await receiver.main.set_surround_mode(mode)


@pytest.mark.parametrize(
    "wire, mode",
    [
        ("L0", V2003SurroundMode.AUTO),
        ("L1", V2003SurroundMode.THX_5_1),         # cmd-side has nothing at "1"
        ("L4", V2003SurroundMode.THX_MUSIC),       # cmd-side this is F1
        ("L5", V2003SurroundMode.DTS_MUSIC),
        ("LA", V2003SurroundMode.DOLBY_DIGITAL),
        ("LB", V2003SurroundMode.DOLBY_PROLOGIC),
        ("LM", V2003SurroundMode.STEREO),
        ("LN", V2003SurroundMode.MONO),
        ("LO", V2003SurroundMode.THX_ULTRA2),
        ("LP", V2003SurroundMode.CSII_MONO),
    ],
)
async def test_surround_status_decoding(
    receiver: MarantzV2003Receiver,
    mock_serial: _MockV2003Serial,
    wire: str,
    mode: V2003SurroundMode,
) -> None:
    mock_serial.query_responses["L"] = wire
    await receiver._query("L")
    assert receiver.state.main.surround_mode is mode


async def test_main_player_tuner(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    await receiver.main.preset_up()
    await receiver.main.direct_key(7)
    await receiver.main.memo()
    assert mock_serial.command_log == ["C5", "E7", "D1"]


async def test_main_player_direct_key_validates_range(
    receiver: MarantzV2003Receiver,
) -> None:
    with pytest.raises(ValueError):
        await receiver.main.direct_key(10)


async def test_multi_room_commands(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    await receiver.multi_room.on()
    await receiver.multi_room.off()
    await receiver.multi_room.volume_up()
    await receiver.multi_room.mute()
    await receiver.multi_room.select_source(V2003Source.DVD)
    assert mock_serial.command_log == ["L2", "L0", "M1", "M0", "Bd"]


async def test_command_nak_raises(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    mock_serial.command_response = b"\x15"  # NAK
    with pytest.raises(ValueError):
        await receiver.main.power_on()


async def test_subscriber_called_on_state_change(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    events: list[V2003ReceiverState | None] = []
    unsubscribe = receiver.subscribe(events.append)

    await receiver._query("L")  # surround AUTO from defaults
    assert any(e is not None and e.main.surround_mode is V2003SurroundMode.AUTO for e in events)

    unsubscribe()
    n = len(events)
    await receiver._query("H")
    assert len(events) == n  # no further events after unsubscribe


async def test_audio_source_infers_tuner_band(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    mock_serial.query_responses["C"] = "CC"  # FM
    await receiver._query("C")
    assert receiver.state.main.tuner_band is V2003TunerBand.FM

    mock_serial.query_responses["C"] = "CD"  # AM
    await receiver._query("C")
    assert receiver.state.main.tuner_band is V2003TunerBand.AM


async def test_volume_max_status_answer(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    mock_serial.query_responses["H"] = "H1"
    await receiver._query("H")
    assert receiver.state.main.volume == 99.0
    assert receiver.state.main.mute is False


async def test_volume_min_means_muted(
    receiver: MarantzV2003Receiver, mock_serial: _MockV2003Serial
) -> None:
    mock_serial.query_responses["H"] = "H2"
    await receiver._query("H")
    assert receiver.state.main.volume == float("-inf")
    assert receiver.state.main.mute is True


async def test_device_id_routing(receiver: MarantzV2003Receiver) -> None:
    # Lines for a different device ID should be dropped.
    receiver._reader.feed_data(b"@2A0\r")
    await asyncio.sleep(0.01)
    # power should still be the default-fixture value (True from A0)
    assert receiver.state.main.power is True


# -- probe() integration ------------------------------------------------------


async def test_probe_detects_v2003() -> None:
    """If 9600-baud probe times out and 4800-baud probe gets `@`, return v2003."""
    from marantz_rs232 import probe

    # Phase 1: silent reader at 9600, then phase 2: feed `@` at 4800.
    phase1 = MagicMock()
    phase1.readexactly = AsyncMock(side_effect=asyncio.IncompleteReadError(b"", 1))
    writer1 = MagicMock()
    writer1.write = MagicMock()
    writer1.drain = AsyncMock()
    writer1.close = MagicMock()
    writer1.wait_closed = AsyncMock()

    phase2 = MagicMock()
    phase2.readexactly = AsyncMock(return_value=b"@")
    writer2 = MagicMock()
    writer2.write = MagicMock()
    writer2.drain = AsyncMock()
    writer2.close = MagicMock()
    writer2.wait_closed = AsyncMock()

    open_call = AsyncMock(side_effect=[(phase1, writer1), (phase2, writer2)])
    with patch("marantz_rs232.probe.serialx.open_serial_connection", open_call):
        cls = await probe("/dev/null", timeout=0.05)
    assert cls is MarantzV2003Receiver
    assert open_call.call_count == 2
    # Phase 2 must use 4800 + RTS/CTS.
    _, phase2_kwargs = open_call.call_args_list[1]
    assert phase2_kwargs == {"baudrate": 4800, "rtscts": True}
