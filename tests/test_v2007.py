"""Tests for the legacy (SR7002-era) Marantz protocol."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import marantz_rs232.v2007.receiver as v2007_receiver
from marantz_rs232 import (
    V2007ReceiverState,
    V2007Source,
    V2007SurroundCode,
    MarantzV2007Receiver,
)
from marantz_rs232.v2007.protocol import (
    encode_query,
    encode_set_command,
    encode_volume,
    parse_line,
    parse_volume,
)

# Speed up the legacy command timeout for the test suite.
v2007_receiver.V2007_COMMAND_TIMEOUT = 0.02


# -- Wire encoding/decoding ---------------------------------------------------


@pytest.mark.parametrize(
    "db, encoded",
    [
        (0.0, "+000"),
        (-13.0, "-130"),
        (-13.5, "-135"),
        (0.5, "+005"),
        (18.0, "+180"),
        (-80.0, "-800"),
    ],
)
def test_encode_volume(db: float, encoded: str) -> None:
    assert encode_volume(db) == encoded


@pytest.mark.parametrize(
    "wire, db",
    [
        ("000", 0.0),
        ("-13", -13.0),
        ("+18", 18.0),
        ("-130", -13.0),
        ("-135", -13.5),
        ("+005", 0.5),
        ("+180", 18.0),
        ("-800", -80.0),
    ],
)
def test_parse_volume(wire: str, db: float) -> None:
    assert parse_volume(wire) == db


def test_parse_volume_mute_sentinel() -> None:
    assert parse_volume("-ZZZ") == float("-inf")


def test_encode_volume_below_min_returns_mute_sentinel() -> None:
    assert encode_volume(float("-inf")) == "-ZZZ"


def test_encode_volume_above_max_raises() -> None:
    with pytest.raises(ValueError):
        encode_volume(20.0)


def test_encode_set_command() -> None:
    assert encode_set_command("PWR", "2") == b"@PWR:2\r"


def test_encode_query() -> None:
    assert encode_query("VOL") == b"@VOL:?\r"


@pytest.mark.parametrize(
    "line, expected",
    [
        ("@PWR:2\r", ("PWR", ":", "2")),
        ("@VOL:-13", ("VOL", ":", "-13")),
        ("@SRC:CC", ("SRC", ":", "CC")),
        ("@MPW=2", ("MPW", "=", "2")),  # Multi Room B uses '=' separator
        ("@CHN*WXYZ", ("CHN", "*", "WXYZ")),  # HD Radio uses '*' separator
        ("PWR:2", ("PWR", ":", "2")),  # leading @ optional
    ],
)
def test_parse_line(line: str, expected: tuple[str, str, str]) -> None:
    assert parse_line(line) == expected


@pytest.mark.parametrize("line", ["@\x06\r", "@\x15\r", "", "@\r"])
def test_parse_line_returns_none_for_ack_or_empty(line: str) -> None:
    assert parse_line(line) is None


# -- MockSerialConnection (legacy variant) ------------------------------------


class _MockSerial:
    """Mock serial reader/writer pair for the @CMD: protocol."""

    def __init__(self) -> None:
        self.reader = asyncio.StreamReader()
        self.writer = MagicMock()
        self.writer.write = MagicMock()
        self.writer.drain = AsyncMock()
        self.writer.close = MagicMock()
        self.writer.wait_closed = AsyncMock()
        self.written: list[bytes] = []
        self.query_responses: dict[str, list[str]] = {}
        self.command_handler: Callable[[str, str], None] | None = None
        self.writer.write.side_effect = self._on_write

    def _on_write(self, data: bytes) -> None:
        self.written.append(data)
        text = data.decode("ascii").rstrip("\r")
        # Parse @PREFIX:VALUE
        if not text.startswith("@"):
            return
        body = text[1:]
        if ":" not in body:
            return
        prefix, _, value = body.partition(":")
        if value == "?":
            for resp in self.query_responses.get(prefix, []):
                self.feed(resp)
        elif self.command_handler is not None:
            self.command_handler(prefix, value)

    def feed(self, line: str) -> None:
        if not line.endswith("\r"):
            line = line + "\r"
        if not line.startswith("@"):
            line = "@" + line
        self.reader.feed_data(line.encode("ascii"))


_DEFAULT_V2007_RESPONSES: dict[str, list[str]] = {
    "PWR": ["PWR:2"],
    "ATT": ["ATT:1"],
    "AMT": ["AMT:1"],
    "VMT": ["VMT:1"],
    "VOL": ["VOL:-13"],
    "TOB": ["TOB:+00"],
    "TOT": ["TOT:+00"],
    "SRC": ["SRC:CC"],
    "71C": ["71C:1"],
    "SPK": ["SPK:21"],
    "HDM": ["HDM:1"],
    "HAM": ["HAM:1"],
    "IPC": ["IPC:2"],
    "SLP": ["SLP:000"],
    "MNU": ["MNU:1"],
    "DCT": ["DCT:11"],
    "FKL": ["FKL:1"],
    "SUR": ["SUR:0"],
    "THX": ["THX:0"],
    "EQM": ["EQM:0"],
    "DHM": ["DHM:0"],
    "NGT": ["NGT:1"],
    "MDA": ["MDA:1"],
    "LIP": ["LIP:000"],
    "TTO": ["TTO:100"],
    "TFQ": ["TFQ:08750"],
    "TPR": ["TPR:01"],
    "TMD": ["TMD:2"],
    "TPI": ["TPI:1"],
    "INP": ["INP:4"],
    "ISG": ["ISG:4"],
    "IST": ["IST:2"],
    "SIG": ["SIG:A"],
    "SFQ": ["SFQ:5"],
    "CHS": ["CHS:F0"],
    "RSV": ["RSV:1.00"],
    "AST": ["AST:F"],
}


@pytest.fixture
async def mock_serial() -> _MockSerial:
    return _MockSerial()


@pytest.fixture
async def receiver(mock_serial: _MockSerial):
    """Create a connected MarantzV2007Receiver with mocked serial."""
    recv = MarantzV2007Receiver("/dev/ttyUSB0")
    mock_serial.query_responses = dict(_DEFAULT_V2007_RESPONSES)

    async def fake_open(*_a, **_kw):
        return mock_serial.reader, mock_serial.writer

    with patch(
        "marantz_rs232.v2007.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        await recv.connect()
        await recv.query_state()

    mock_serial.query_responses.clear()

    yield recv

    if recv.connected:
        await recv.disconnect()


# -- Connection lifecycle -----------------------------------------------------


async def test_connect_verifies_with_pwr_query(mock_serial: _MockSerial) -> None:
    recv = MarantzV2007Receiver("/dev/ttyUSB0")
    mock_serial.query_responses = {"PWR": ["PWR:2"]}

    async def fake_open(*_a, **_kw):
        return mock_serial.reader, mock_serial.writer

    with patch(
        "marantz_rs232.v2007.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        await recv.connect()
        try:
            assert recv.connected
            assert recv.state.main.power is True
            # First write should be the PWR query.
            assert mock_serial.written[0] == b"@PWR:?\r"
        finally:
            await recv.disconnect()


async def test_connect_raises_when_no_response(mock_serial: _MockSerial) -> None:
    recv = MarantzV2007Receiver("/dev/ttyUSB0")
    # No responses registered → query times out.

    async def fake_open(*_a, **_kw):
        return mock_serial.reader, mock_serial.writer

    with patch(
        "marantz_rs232.v2007.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        with pytest.raises(ConnectionError):
            await recv.connect()


async def test_connect_enables_auto_status_feedback(mock_serial: _MockSerial) -> None:
    recv = MarantzV2007Receiver("/dev/ttyUSB0")
    mock_serial.query_responses = {"PWR": ["PWR:2"]}

    async def fake_open(*_a, **_kw):
        return mock_serial.reader, mock_serial.writer

    with patch(
        "marantz_rs232.v2007.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        await recv.connect()
        try:
            assert b"@AST:F\r" in mock_serial.written
        finally:
            await recv.disconnect()


# -- Query state --------------------------------------------------------------


async def test_query_state_populates_all_fields(receiver: MarantzV2007Receiver) -> None:
    s = receiver.state.main
    assert s.power is True
    assert s.mute is False
    assert s.video_mute is False
    assert s.volume == -13.0
    assert s.bass == 0
    assert s.treble == 0
    assert s.source_video == "C"
    assert s.source_audio == "C"
    assert s.surround_mode == "0"
    assert s.sleep_minutes == 0


# -- Commands -----------------------------------------------------------------


async def test_power_on_sends_pwr_2(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.power_on()
    assert b"@PWR:2\r" in mock_serial.written


async def test_power_off_sends_pwr_1(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.power_off()
    assert b"@PWR:1\r" in mock_serial.written


async def test_mute_on_sends_amt_2(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.mute_on()
    assert b"@AMT:2\r" in mock_serial.written


async def test_set_volume_encodes_correctly(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_volume(-13.5)
    assert b"@VOL:0-135\r" in mock_serial.written


async def test_set_volume_zero(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_volume(0.0)
    assert b"@VOL:0+000\r" in mock_serial.written


async def test_volume_up_sends_vol_1(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.volume_up()
    assert b"@VOL:1\r" in mock_serial.written


async def test_set_bass(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_bass(-3)
    assert b"@TOB:0-03\r" in mock_serial.written


async def test_set_treble_positive(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_treble(6)
    assert b"@TOT:0+06\r" in mock_serial.written


async def test_set_bass_out_of_range(receiver: MarantzV2007Receiver) -> None:
    with pytest.raises(ValueError):
        await receiver.main.set_bass(10)


async def test_select_source_with_enum(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.select_source(V2007Source.CD_CDR)
    assert b"@SRC:C\r" in mock_serial.written


async def test_select_source_with_string(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.select_source("F")
    assert b"@SRC:F\r" in mock_serial.written


async def test_set_surround_prepends_zero(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_surround_mode(V2007SurroundCode.AUTO.value)
    assert b"@SUR:00\r" in mock_serial.written


async def test_surround_next(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.surround_next()
    assert b"@SUR:1\r" in mock_serial.written


async def test_set_sleep(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_sleep(30)
    assert b"@SLP:0030\r" in mock_serial.written


async def test_sleep_off(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.sleep_off()
    assert b"@SLP:1\r" in mock_serial.written


async def test_set_sleep_out_of_range(receiver: MarantzV2007Receiver) -> None:
    with pytest.raises(ValueError):
        await receiver.main.set_sleep(200)


# -- Event handling / state updates from auto-feedback -----------------------


async def test_unsolicited_volume_update_propagates(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    updates: list[V2007ReceiverState | None] = []
    receiver.subscribe(lambda s: updates.append(s))

    mock_serial.feed("VOL:-25")
    await asyncio.sleep(0.05)

    assert receiver.state.main.volume == -25.0
    assert updates and updates[0].main.volume == -25.0


async def test_unsolicited_source_update_propagates(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.feed("SRC:F2")  # video=F (TUNER1), audio=2 (DVD)
    await asyncio.sleep(0.05)

    assert receiver.state.main.source_video == "F"
    assert receiver.state.main.source_audio == "2"


async def test_query_returns_response_value(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.query_responses = {"VOL": ["VOL:-25"]}
    result = await receiver.main.query_volume()
    assert result == -25.0


# -- Disconnect / teardown ---------------------------------------------------


async def test_disconnect_notifies_subscribers_with_none(
    receiver: MarantzV2007Receiver,
) -> None:
    updates: list[V2007ReceiverState | None] = []
    receiver.subscribe(lambda s: updates.append(s))

    await receiver.disconnect()

    assert updates[-1] is None
    assert not receiver.connected


# -- Phase 2: extended commands ---------------------------------------------


from marantz_rs232 import (
    V2007DolbyHeadphone,
    V2007EQMode,
    V2007HDMIAudioMode,
    V2007HDMIChannel,
    V2007IPConverter,
    V2007MDAX,
    V2007Menu,
    V2007Model,
    V2007NightMode,
    V2007StereoMode,
    V2007THXSet,
    V2007TunerMode,
    V2007VolumeMode,
)
from marantz_rs232.v2007.protocol import (
    decode_tuner_frequency,
    encode_tone,
    encode_tuner_frequency_am_khz,
    encode_tuner_frequency_fm_mhz,
    encode_tuner_xm_channel,
)


# -- Tone / tuner / lip-sync encoding --------------------------------------


@pytest.mark.parametrize(
    "db, encoded",
    [(0, "+00"), (-3, "-03"), (6, "+06"), (-6, "-06")],
)
def test_encode_tone(db: int, encoded: str) -> None:
    assert encode_tone(db) == encoded


def test_encode_tuner_frequency_am() -> None:
    assert encode_tuner_frequency_am_khz(1080) == "01080"


def test_encode_tuner_frequency_fm() -> None:
    assert encode_tuner_frequency_fm_mhz(87.50) == "08750"


def test_encode_tuner_xm() -> None:
    assert encode_tuner_xm_channel(42) == "00042"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("00042", ("XM", 42.0)),
        ("01080", ("AM", 1080.0)),
        ("08750", ("FM", 87.50)),
    ],
)
def test_decode_tuner_frequency(
    raw: str, expected: tuple[str, float]
) -> None:
    assert decode_tuner_frequency(raw) == expected


def test_encode_tuner_fm_below_min_raises() -> None:
    with pytest.raises(ValueError):
        encode_tuner_frequency_fm_mhz(10.0)


# -- Phase 2 query state population ----------------------------------------


async def test_query_state_populates_phase2_fields(
    receiver: MarantzV2007Receiver,
) -> None:
    s = receiver.state.main
    # Phase 1 fields still populated (regression check)
    assert s.power is True
    # Phase 2 fields
    assert s.attenuator is False
    assert s.seven_one_input is False
    assert s.speaker_a is True
    assert s.speaker_b is False
    assert s.hdmi_channel is V2007HDMIChannel.CH1
    assert s.hdmi_audio_mode is V2007HDMIAudioMode.ENABLE
    assert s.ip_converter is V2007IPConverter.ENABLE
    assert s.front_key_lock is False
    assert s.dc_trigger_1 is False
    assert s.dc_trigger_2 is False
    assert s.thx_mode == "0"
    assert s.eq_mode is V2007EQMode.OFF
    assert s.dolby_headphone_mode is V2007DolbyHeadphone.BYPASS
    assert s.night_mode is V2007NightMode.OFF
    assert s.mdax is V2007MDAX.OFF
    assert s.lip_sync_ms == 0
    assert s.tuner_frequency_raw == "08750"
    assert s.tuner_preset == 1
    assert s.tuner_mode is V2007TunerMode.AUTO
    assert s.firmware_version == "1.00"


# -- Phase 2 command tests --------------------------------------------------


async def test_set_thx_mode(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_thx_mode(V2007THXSet.CINEMA)
    assert b"@THX:5\r" in mock_serial.written


async def test_set_eq_mode(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_eq_mode(V2007EQMode.AUDYSSEY_CURVE)
    assert b"@EQM:5\r" in mock_serial.written


async def test_set_night_mode_auto(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_night_mode(V2007NightMode.AUTO)
    assert b"@NGT:3\r" in mock_serial.written


async def test_set_mdax(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_mdax(V2007MDAX.HIGH)
    assert b"@MDA:3\r" in mock_serial.written


async def test_set_lip_sync(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_lip_sync(80)
    assert b"@LIP:0080\r" in mock_serial.written


async def test_speaker_a_on(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.speaker_a_on()
    assert b"@SPK:2\r" in mock_serial.written


async def test_set_hdmi_channel(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_hdmi_channel(V2007HDMIChannel.CH2)
    assert b"@HDM:2\r" in mock_serial.written


async def test_attenuator_on(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.attenuator_on()
    assert b"@ATT:2\r" in mock_serial.written


async def test_dc_trigger_1_on(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.dc_trigger_1_on()
    assert b"@DCT:12\r" in mock_serial.written


async def test_dc_trigger_2_off(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.dc_trigger_2_off()
    assert b"@DCT:21\r" in mock_serial.written


async def test_set_tuner_fm(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_tuner_fm_frequency(101.10)
    assert b"@TFQ:010110\r" in mock_serial.written


async def test_set_tuner_preset(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.main.set_tuner_preset(7)
    assert b"@TPR:007\r" in mock_serial.written


async def test_decode_tuner_frequency_via_receiver(
    receiver: MarantzV2007Receiver,
) -> None:
    # Default state has TFQ:08750 → FM 87.50 MHz
    band, value = receiver.decode_tuner_frequency()
    assert band == "FM"
    assert value == 87.50


# -- DCT and SPK 2-char status parsing -------------------------------------


async def test_dct_status_propagates_both_triggers(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.feed("DCT:22")
    await asyncio.sleep(0.05)
    assert receiver.state.main.dc_trigger_1 is True
    assert receiver.state.main.dc_trigger_2 is True


async def test_spk_status_propagates_both_speakers(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.feed("SPK:12")
    await asyncio.sleep(0.05)
    assert receiver.state.main.speaker_a is False
    assert receiver.state.main.speaker_b is True


async def test_unsolicited_thx_update(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.feed("THX:e")  # CINEMA per status table
    await asyncio.sleep(0.05)
    assert receiver.state.main.thx_mode == "e"


async def test_unsolicited_signal_format_update(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    from marantz_rs232 import V2007SignalFormat

    mock_serial.feed("SIG:H")  # DD True HD
    await asyncio.sleep(0.05)
    assert receiver.state.main.signal_format is V2007SignalFormat.DD_TRUE_HD


# -- Multi Room A ------------------------------------------------------------


async def test_multiroom_a_power_on(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.multi_room_a.power_on()
    assert b"@MPW:2\r" in mock_serial.written


async def test_multiroom_a_set_volume(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.multi_room_a.set_line_volume(-20.0)
    assert b"@MVL:0-200\r" in mock_serial.written


async def test_multiroom_a_select_source(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.multi_room_a.select_source(V2007Source.TUNER1)
    assert b"@MSC:F\r" in mock_serial.written


async def test_multiroom_a_state_updates(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.feed("MPW:2")
    mock_serial.feed("MVL:-15")
    mock_serial.feed("MSC:0F")  # video=0 (off), audio=F (TUNER1)
    await asyncio.sleep(0.05)

    a = receiver.state.multi_room_a
    assert a.power is True
    assert a.line_volume == -15.0
    assert a.source_video == "0"
    assert a.source_audio == "F"


async def test_multiroom_a_set_stereo_mode(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.multi_room_a.set_stereo_mode(V2007StereoMode.MONO)
    assert b"@MST:2\r" in mock_serial.written


# -- Multi Room B (= separator, SR8002) ------------------------------------


async def test_multiroom_b_power_on_uses_equals_separator(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.written.clear()
    await receiver.multi_room_b.power_on()
    assert b"@MPW=2\r" in mock_serial.written


async def test_multiroom_b_state_updates_via_equals_separator(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    # Receiver echoes back with `=` separator
    mock_serial.reader.feed_data(b"@MPW=2\r")
    mock_serial.reader.feed_data(b"@MVL=-30\r")
    await asyncio.sleep(0.05)

    b = receiver.state.multi_room_b
    assert b.power is True
    assert b.line_volume == -30.0
    # Multi Room A is unchanged
    assert receiver.state.multi_room_a.power is None


# -- HD Radio metadata (* separator, SR8002) ------------------------------


async def test_hd_radio_metadata_updates_state(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    mock_serial.reader.feed_data(b"@CHN*WBEZ FM 91.5\r")
    mock_serial.reader.feed_data(b"@SON*MORNING EDITION\r")
    await asyncio.sleep(0.05)

    m = receiver.state.main
    assert m.hd_station_name == "WBEZ FM 91.5"
    assert m.hd_program_service == "MORNING EDITION"


# -- Status-only queries ---------------------------------------------------


async def test_query_firmware_version(receiver: MarantzV2007Receiver) -> None:
    assert receiver.state.main.firmware_version == "1.00"


async def test_input_signal_status(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial
) -> None:
    from marantz_rs232 import V2007InputSignal

    mock_serial.feed("ISG:2")
    await asyncio.sleep(0.05)
    assert receiver.state.main.input_signal is V2007InputSignal.DIGITAL


# -- Auto Lip Sync (HAL → ALS asymmetry) ----------------------------------


async def test_query_auto_lip_sync_uses_als_response(
    mock_serial: _MockSerial,
) -> None:
    """The HAL query must accept an ALS response per the spec."""
    recv = MarantzV2007Receiver("/dev/ttyUSB0")
    mock_serial.query_responses = {
        "PWR": ["PWR:2"],
        # Mock returns ALS response when HAL is queried.
        "HAL": ["ALS:2"],
    }

    async def fake_open(*_a, **_kw):
        return mock_serial.reader, mock_serial.writer

    with patch(
        "marantz_rs232.v2007.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        await recv.connect()
        try:
            result = await recv.main.query_auto_lip_sync()
            assert result is True
            assert recv.state.main.auto_lip_sync is True
        finally:
            await recv.disconnect()


# -- Model parameter -------------------------------------------------------


def test_model_defaults_to_generic() -> None:
    r = MarantzV2007Receiver("/dev/null")
    assert r.model is V2007Model.GENERIC


def test_model_can_be_specified() -> None:
    r = MarantzV2007Receiver("/dev/null", model=V2007Model.SR8002)
    assert r.model is V2007Model.SR8002


# -- Per-model gating warnings --------------------------------------------


async def test_sr8002_only_command_warns_on_sr7002(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial, caplog
) -> None:
    """SR8002-only commands should warn when called on a non-SR8002 model."""
    import logging
    from marantz_rs232 import V2007Component2

    caplog.set_level(logging.WARNING)
    mock_serial.written.clear()

    await receiver.main.set_component2(V2007Component2.MAIN)

    # The command is still sent (graceful fallback) ...
    assert b"@CM2:1\r" in mock_serial.written
    # ... but a warning was logged.
    assert any("SR8002-only" in rec.message for rec in caplog.records)


async def test_sr8002_only_command_silent_on_sr8002_model(
    mock_serial: _MockSerial, caplog
) -> None:
    """The same command should not warn when the model is set to SR8002."""
    import logging
    from marantz_rs232 import V2007Component2

    recv = MarantzV2007Receiver("/dev/ttyUSB0", model=V2007Model.SR8002)
    mock_serial.query_responses = {"PWR": ["PWR:2"]}

    async def fake_open(*_a, **_kw):
        return mock_serial.reader, mock_serial.writer

    caplog.set_level(logging.WARNING)
    with patch(
        "marantz_rs232.v2007.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        await recv.connect()
        try:
            mock_serial.written.clear()
            caplog.clear()
            await recv.main.set_component2(V2007Component2.MAIN)
            assert b"@CM2:1\r" in mock_serial.written
            assert not any(
                "SR8002-only" in rec.message for rec in caplog.records
            )
        finally:
            await recv.disconnect()


async def test_multi_room_b_warns_on_sr7002(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial, caplog
) -> None:
    """Sending via the `=` separator should warn when model isn't SR8002."""
    import logging

    caplog.set_level(logging.WARNING)
    mock_serial.written.clear()

    await receiver.multi_room_b.power_on()

    assert b"@MPW=2\r" in mock_serial.written
    assert any("SR8002" in rec.message for rec in caplog.records)


async def test_warning_only_logged_once_per_feature(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial, caplog
) -> None:
    """Repeated calls to the same SR8002-only feature warn once, not every time."""
    import logging
    from marantz_rs232 import V2007Component2

    caplog.set_level(logging.WARNING)

    await receiver.main.set_component2(V2007Component2.MAIN)
    await receiver.main.set_component2(V2007Component2.MULTI)
    await receiver.main.set_component2(V2007Component2.MAIN)

    component2_warnings = [
        rec for rec in caplog.records if "Component2" in rec.message
    ]
    assert len(component2_warnings) == 1


async def test_hd_radio_query_warns_on_sr7002(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial, caplog
) -> None:
    """HD Radio metadata queries warn on non-SR8002 models."""
    import logging

    caplog.set_level(logging.WARNING)

    await receiver.query_hd_radio_metadata()

    assert any("HD Radio" in rec.message for rec in caplog.records)


async def test_digital_auto_tuner_mode_warns_on_sr7002(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial, caplog
) -> None:
    """V2007TunerMode.DIGITAL_AUTO is HD-only and warns on non-SR8002 models."""
    import logging

    caplog.set_level(logging.WARNING)

    await receiver.main.set_tuner_mode(V2007TunerMode.DIGITAL_AUTO)

    assert any("HD Radio" in rec.message for rec in caplog.records)


async def test_non_hd_tuner_mode_does_not_warn(
    receiver: MarantzV2007Receiver, mock_serial: _MockSerial, caplog
) -> None:
    """Setting AUTO or MONO on the SR7002 should not trigger warnings."""
    import logging

    caplog.set_level(logging.WARNING)

    await receiver.main.set_tuner_mode(V2007TunerMode.AUTO)
    await receiver.main.set_tuner_mode(V2007TunerMode.MONO)

    assert not any("SR8002" in rec.message for rec in caplog.records)
