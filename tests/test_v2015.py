"""Tests for marantz_rs232 query, control, and event handling."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from conftest import (
    DEFAULT_QUERY_RESPONSES,
    MockSerialConnection,
    connect_with_defaults,
)

from marantz_rs232 import (
    _V2015_MULTI_RESPONSE_PREFIXES,
    _V2015_SINGLE_RESPONSE_PREFIXES,
    V2015AspectMode,
    V2015AudioDecodeMode,
    V2015DComp,
    V2015DialogEnhancer,
    V2015DigitalInputMode,
    V2015DimmerMode,
    V2015DRC,
    V2015DynamicVolume,
    V2015EcoMode,
    V2015HDMIAudioOutput,
    V2015HDMIMonitor,
    V2015HDMIResolution,
    V2015InputSource,
    V2015MDAX,
    V2015MainZoneState,
    MarantzV2015Receiver,
    V2015MultEQ,
    V2015ReceiverState,
    V2015TunerBand,
    V2015TunerMode,
    V2015VideoProcessMode,
    V2015Zone4State,
    V2015ZoneChannelMode,
    _v2015_channel_volume_to_param,
    _v2015_parse_channel_volume_param,
    _v2015_parse_volume_param,
    _v2015_volume_to_param,
)


# -- Master volume conversion tests --


def test_parse_volume_zero_db():
    assert _v2015_parse_volume_param("80") == 0.0


def test_parse_volume_max_18db():
    assert _v2015_parse_volume_param("98") == 18.0


def test_parse_volume_min():
    assert _v2015_parse_volume_param("99") == -80.0


def test_parse_volume_negative():
    assert _v2015_parse_volume_param("60") == -20.0


def test_parse_volume_half_db_positive():
    assert _v2015_parse_volume_param("805") == 0.5


def test_parse_volume_half_db_negative():
    assert _v2015_parse_volume_param("795") == -0.5


def test_parse_volume_half_db_large():
    assert _v2015_parse_volume_param("505") == -29.5


def test_volume_to_param_zero_db():
    assert _v2015_volume_to_param(0.0) == "80"


def test_volume_to_param_max():
    assert _v2015_volume_to_param(18.0) == "98"


def test_volume_to_param_min():
    assert _v2015_volume_to_param(-80.0) == "99"


def test_volume_to_param_negative():
    assert _v2015_volume_to_param(-20.0) == "60"


def test_volume_to_param_half_db():
    assert _v2015_volume_to_param(0.5) == "805"


def test_volume_to_param_half_db_negative():
    assert _v2015_volume_to_param(-0.5) == "795"


def test_volume_roundtrip():
    for db in [-80, -20, -10.5, -0.5, 0, 0.5, 10, 18]:
        assert _v2015_parse_volume_param(_v2015_volume_to_param(db)) == db


# -- Channel volume conversion tests --


def test_parse_channel_volume_zero_db():
    assert _v2015_parse_channel_volume_param("50") == 0.0


def test_parse_channel_volume_max():
    assert _v2015_parse_channel_volume_param("62") == 12.0


def test_parse_channel_volume_min():
    assert _v2015_parse_channel_volume_param("38") == -12.0


def test_parse_channel_volume_off():
    assert _v2015_parse_channel_volume_param("00") == -50.0


def test_parse_channel_volume_half_db():
    assert _v2015_parse_channel_volume_param("505") == 0.5


def test_channel_volume_to_param_zero():
    assert _v2015_channel_volume_to_param(0.0) == "50"


def test_channel_volume_to_param_max():
    assert _v2015_channel_volume_to_param(12.0) == "62"


def test_channel_volume_to_param_min():
    assert _v2015_channel_volume_to_param(-12.0) == "38"


def test_channel_volume_to_param_half():
    assert _v2015_channel_volume_to_param(0.5) == "505"


def test_channel_volume_roundtrip():
    for db in [-12, -6.5, -1, 0, 0.5, 6, 12]:
        assert _v2015_parse_channel_volume_param(_v2015_channel_volume_to_param(db)) == db


# -- State tests --


def test_initial_state():
    state = V2015ReceiverState()
    assert state.power is None
    assert state.main_zone.power is None
    assert state.main_zone.mute is None
    assert state.main_zone.volume is None
    assert state.main_zone.volume_max is None
    assert state.main_zone.volume_min is None
    assert state.main_zone.input_source is None
    assert state.main_zone.surround_mode is None
    assert state.main_zone.channel_volumes == {}
    assert state.zone_2.power is None
    assert state.zone_2.mute is None
    assert state.zone_3.power is None
    assert state.zone_3.mute is None


def test_state_copy():
    state = V2015ReceiverState(
        power=True,
        main_zone=V2015MainZoneState(
            volume=0.0,
            volume_max=18.0,
            volume_min=-80.0,
        ),
    )
    state.main_zone.channel_volumes["FL"] = 0.0
    state.zone_2.power = True
    copy = state.copy()
    assert copy.power is True
    assert copy.main_zone.volume == 0.0
    assert copy.main_zone.volume_max == 18.0
    assert copy.main_zone.volume_min == -80.0
    assert copy.main_zone.channel_volumes == {"FL": 0.0}
    assert copy.zone_2.power is True
    copy.power = False
    copy.main_zone.channel_volumes["FL"] = 5.0
    copy.zone_2.power = False
    assert state.power is True
    assert state.main_zone.channel_volumes["FL"] == 0.0
    assert state.zone_2.power is True


# -- Connection tests --


async def test_connect_verifies_power(mock_serial):
    recv = MarantzV2015Receiver("/dev/ttyUSB0")

    async def fake_open(*args, **kwargs):
        return mock_serial.reader, mock_serial.writer

    mock_serial._query_responses = dict(DEFAULT_QUERY_RESPONSES)

    with patch(
        "marantz_rs232.v2015.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        await recv.connect()

    assert recv.state.power is True
    sent_queries = [data.decode("ascii") for data in mock_serial.written_data]
    assert sent_queries == ["PW?\r"]

    await recv.disconnect()


async def test_query_state_populates_full_state(receiver):
    state = receiver.state
    assert state.power is True
    assert state.main_zone.power is True
    assert state.main_zone.volume == 0.0
    assert state.main_zone.volume_max == 18.0
    assert state.main_zone.volume_min == -80.0
    assert state.main_zone.mute is False
    assert state.main_zone.input_source == V2015InputSource.CD
    assert state.main_zone.surround_mode == "STEREO"
    assert state.main_zone.digital_input == V2015DigitalInputMode.AUTO
    assert state.main_zone.audio_decode == V2015AudioDecodeMode.AUTO
    assert state.main_zone.video_select == V2015InputSource.DVD
    assert state.main_zone.sleep is None
    assert state.main_zone.eco == V2015EcoMode.OFF
    assert state.main_zone.auto_standby is None
    assert state.main_zone.tone_control is False
    assert state.main_zone.bass == 0
    assert state.main_zone.treble == 0
    assert state.main_zone.cinema_eq is False
    assert state.main_zone.multeq == V2015MultEQ.AUDYSSEY
    assert state.main_zone.dynamic_eq is False
    assert state.main_zone.dynamic_volume == V2015DynamicVolume.OFF
    assert state.main_zone.drc == V2015DRC.OFF
    assert state.main_zone.channel_volumes["FL"] == 0.0
    assert state.main_zone.channel_volumes["FR"] == 0.0
    assert state.zone_2.power is False
    assert state.zone_3.power is False


async def test_receiver_exposes_shared_player_objects(receiver):
    assert receiver.power is True
    assert receiver.main.power is True
    assert receiver.main.input_source == V2015InputSource.CD
    assert receiver.main.volume == 0.0
    assert receiver.main.volume_min == -80.0
    assert receiver.main.volume_max == 18.0
    assert receiver.main.mute is False
    assert receiver.zone_2.power is False
    assert receiver.zone_3.power is False


async def test_query_state_queries_all_prefixes(mock_serial):
    recv = await connect_with_defaults(mock_serial)

    expected = set(_V2015_SINGLE_RESPONSE_PREFIXES) | set(_V2015_MULTI_RESPONSE_PREFIXES)
    sent_queries = {
        data[:-1].decode("ascii").replace("?", "")
        for data in mock_serial.written_data
        if data.endswith(b"?\r")
    }
    assert expected == sent_queries

    await recv.disconnect()


async def test_connect_timeout_raises():
    recv = MarantzV2015Receiver("/dev/ttyUSB0")
    mock = MockSerialConnection()

    async def fake_open(*args, **kwargs):
        return mock.reader, mock.writer

    with patch(
        "marantz_rs232.v2015.receiver.serialx.open_serial_connection",
        side_effect=fake_open,
    ):
        with pytest.raises(ConnectionError, match="No response"):
            await recv.connect()


async def test_disconnect(receiver):
    await receiver.disconnect()
    assert not receiver.connected


async def test_written_command_format(receiver, mock_serial):
    assert b"PW?\r" in mock_serial.written_data


# -- Power & main zone command tests --


async def test_power_on(receiver, mock_serial):
    await receiver.power_on()
    assert b"PWON\r" in mock_serial.written_data


async def test_power_standby(receiver, mock_serial):
    await receiver.power_standby()
    assert b"PWSTANDBY\r" in mock_serial.written_data


async def test_main_player_power_on(receiver, mock_serial):
    await receiver.main.power_on()
    assert b"ZMON\r" in mock_serial.written_data


async def test_main_player_power_standby(receiver, mock_serial):
    await receiver.main.power_standby()
    assert b"ZMOFF\r" in mock_serial.written_data


# -- Master volume command tests --


async def test_volume_up(receiver, mock_serial):
    await receiver.main.volume_up()
    assert b"MVUP\r" in mock_serial.written_data


async def test_volume_down(receiver, mock_serial):
    await receiver.main.volume_down()
    assert b"MVDOWN\r" in mock_serial.written_data


async def test_set_volume(receiver, mock_serial):
    await receiver.main.set_volume(0.0)
    assert b"MV80\r" in mock_serial.written_data


async def test_set_volume_half_db(receiver, mock_serial):
    await receiver.main.set_volume(-10.5)
    assert b"MV695\r" in mock_serial.written_data


# -- Channel volume command tests --


async def test_channel_volume_up(receiver, mock_serial):
    await receiver.main.channel_volume_up("FL")
    assert b"CVFL UP\r" in mock_serial.written_data


async def test_channel_volume_down(receiver, mock_serial):
    await receiver.main.channel_volume_down("C")
    assert b"CVC DOWN\r" in mock_serial.written_data


async def test_set_channel_volume(receiver, mock_serial):
    await receiver.main.set_channel_volume("SW", 3.0)
    assert b"CVSW 53\r" in mock_serial.written_data


async def test_set_channel_volume_half_db(receiver, mock_serial):
    await receiver.main.set_channel_volume("FR", -2.5)
    assert b"CVFR 475\r" in mock_serial.written_data


# -- Mute command tests --


async def test_mute_on(receiver, mock_serial):
    await receiver.main.mute_on()
    assert b"MUON\r" in mock_serial.written_data


async def test_mute_off(receiver, mock_serial):
    await receiver.main.mute_off()
    assert b"MUOFF\r" in mock_serial.written_data


# -- Input source command tests --


async def test_select_input_source(receiver, mock_serial):
    await receiver.main.select_input_source(V2015InputSource.DVD)
    assert b"SIDVD\r" in mock_serial.written_data


async def test_select_input_source_with_slash(receiver, mock_serial):
    await receiver.main.select_input_source(V2015InputSource.SAT_CBL)
    assert b"SISAT/CBL\r" in mock_serial.written_data


# -- Surround mode command tests --


async def test_set_surround_mode(receiver, mock_serial):
    await receiver.main.set_surround_mode("STEREO")
    assert b"MSSTEREO\r" in mock_serial.written_data


async def test_set_surround_mode_with_spaces(receiver, mock_serial):
    await receiver.main.set_surround_mode("DOLBY DIGITAL")
    assert b"MSDOLBY DIGITAL\r" in mock_serial.written_data


# -- Parameter settings command tests --


async def test_tone_control_on(receiver, mock_serial):
    await receiver.main.tone_control_on()
    assert b"PSTONE CTRL ON\r" in mock_serial.written_data


async def test_tone_control_off(receiver, mock_serial):
    await receiver.main.tone_control_off()
    assert b"PSTONE CTRL OFF\r" in mock_serial.written_data


async def test_set_bass(receiver, mock_serial):
    await receiver.main.set_bass(3)
    assert b"PSBAS 53\r" in mock_serial.written_data


async def test_bass_up(receiver, mock_serial):
    await receiver.main.bass_up()
    assert b"PSBAS UP\r" in mock_serial.written_data


async def test_set_treble(receiver, mock_serial):
    await receiver.main.set_treble(-2)
    assert b"PSTRE 48\r" in mock_serial.written_data


async def test_treble_up(receiver, mock_serial):
    await receiver.main.treble_up()
    assert b"PSTRE UP\r" in mock_serial.written_data


async def test_cinema_eq_on(receiver, mock_serial):
    await receiver.main.cinema_eq_on()
    assert b"PSCINEMA EQ.ON\r" in mock_serial.written_data


async def test_cinema_eq_off(receiver, mock_serial):
    await receiver.main.cinema_eq_off()
    assert b"PSCINEMA EQ.OFF\r" in mock_serial.written_data


async def test_set_multeq(receiver, mock_serial):
    await receiver.main.set_multeq(V2015MultEQ.FLAT)
    assert b"PSMULTEQ:FLAT\r" in mock_serial.written_data


async def test_dynamic_eq_on(receiver, mock_serial):
    await receiver.main.dynamic_eq_on()
    assert b"PSDYNEQ ON\r" in mock_serial.written_data


async def test_dynamic_eq_off(receiver, mock_serial):
    await receiver.main.dynamic_eq_off()
    assert b"PSDYNEQ OFF\r" in mock_serial.written_data


async def test_set_dynamic_volume(receiver, mock_serial):
    await receiver.main.set_dynamic_volume(V2015DynamicVolume.MED)
    assert b"PSDYNVOL MED\r" in mock_serial.written_data


async def test_set_drc(receiver, mock_serial):
    await receiver.main.set_drc(V2015DRC.HI)
    assert b"PSDRC HI\r" in mock_serial.written_data


# -- Digital input command tests --


async def test_set_digital_input(receiver, mock_serial):
    await receiver.main.set_digital_input(V2015DigitalInputMode.AUTO)
    assert b"SDAUTO\r" in mock_serial.written_data


async def test_set_digital_input_ext(receiver, mock_serial):
    await receiver.main.set_digital_input(V2015DigitalInputMode.EXT_IN)
    assert b"SDEXT.IN\r" in mock_serial.written_data


# -- Audio decode command tests --


async def test_set_audio_decode(receiver, mock_serial):
    await receiver.main.set_audio_decode(V2015AudioDecodeMode.PCM)
    assert b"DCPCM\r" in mock_serial.written_data


# -- Video select command tests --


async def test_set_video_select(receiver, mock_serial):
    await receiver.main.set_video_select(V2015InputSource.DVD)
    assert b"SVDVD\r" in mock_serial.written_data


async def test_cancel_video_select(receiver, mock_serial):
    await receiver.main.cancel_video_select()
    assert b"SVSOURCE\r" in mock_serial.written_data


# -- Sleep / ECO / Standby / Dimmer command tests --


async def test_set_sleep(receiver, mock_serial):
    await receiver.main.set_sleep(30)
    assert b"SLP030\r" in mock_serial.written_data


async def test_sleep_off(receiver, mock_serial):
    await receiver.main.sleep_off()
    assert b"SLPOFF\r" in mock_serial.written_data


async def test_set_eco(receiver, mock_serial):
    await receiver.main.set_eco(V2015EcoMode.AUTO)
    assert b"ECOAUTO\r" in mock_serial.written_data


async def test_set_auto_standby(receiver, mock_serial):
    await receiver.main.set_auto_standby("2H")
    assert b"STBY2H\r" in mock_serial.written_data


async def test_auto_standby_off(receiver, mock_serial):
    await receiver.main.auto_standby_off()
    assert b"STBYOFF\r" in mock_serial.written_data


async def test_set_dimmer(receiver, mock_serial):
    await receiver.main.set_dimmer(V2015DimmerMode.DIM)
    assert b"DIM DIM\r" in mock_serial.written_data


# -- Tuner command tests (Marantz TFAN/TPAN/TMAN prefixes) --


async def test_tuner_frequency_up(receiver, mock_serial):
    await receiver.main.tuner_frequency_up()
    assert b"TFANUP\r" in mock_serial.written_data


async def test_tuner_frequency_down(receiver, mock_serial):
    await receiver.main.tuner_frequency_down()
    assert b"TFANDOWN\r" in mock_serial.written_data


async def test_set_tuner_frequency(receiver, mock_serial):
    await receiver.main.set_tuner_frequency("105000")
    assert b"TFAN105000\r" in mock_serial.written_data


async def test_tuner_preset_up(receiver, mock_serial):
    await receiver.main.tuner_preset_up()
    assert b"TPANUP\r" in mock_serial.written_data


async def test_tuner_preset_down(receiver, mock_serial):
    await receiver.main.tuner_preset_down()
    assert b"TPANDOWN\r" in mock_serial.written_data


async def test_set_tuner_preset(receiver, mock_serial):
    await receiver.main.set_tuner_preset("A1")
    assert b"TPANA1\r" in mock_serial.written_data


async def test_set_tuner_band(receiver, mock_serial):
    await receiver.main.set_tuner_band(V2015TunerBand.FM)
    assert b"TMANFM\r" in mock_serial.written_data


async def test_set_tuner_mode(receiver, mock_serial):
    await receiver.main.set_tuner_mode(V2015TunerMode.AUTO)
    assert b"TMANAUTO\r" in mock_serial.written_data


# -- Zone 2 command tests --


async def test_zone2_power_on(receiver, mock_serial):
    await receiver.zone_2.power_on()
    assert b"Z2ON\r" in mock_serial.written_data


async def test_zone2_power_standby(receiver, mock_serial):
    await receiver.zone_2.power_standby()
    assert b"Z2OFF\r" in mock_serial.written_data


async def test_zone2_select_input_source(receiver, mock_serial):
    await receiver.zone_2.select_input_source(V2015InputSource.CD)
    assert b"Z2CD\r" in mock_serial.written_data


async def test_zone2_volume_up(receiver, mock_serial):
    await receiver.zone_2.volume_up()
    assert b"Z2UP\r" in mock_serial.written_data


async def test_zone2_set_volume(receiver, mock_serial):
    await receiver.zone_2.set_volume(0.0)
    assert b"Z280\r" in mock_serial.written_data


async def test_zone2_mute_on(receiver, mock_serial):
    await receiver.zone_2.mute_on()
    assert b"Z2MUON\r" in mock_serial.written_data


async def test_zone2_mute_off(receiver, mock_serial):
    await receiver.zone_2.mute_off()
    assert b"Z2MUOFF\r" in mock_serial.written_data


# -- Zone 3 command tests --


async def test_zone3_power_on(receiver, mock_serial):
    await receiver.zone_3.power_on()
    assert b"Z3ON\r" in mock_serial.written_data


async def test_zone3_power_standby(receiver, mock_serial):
    await receiver.zone_3.power_standby()
    assert b"Z3OFF\r" in mock_serial.written_data


async def test_zone3_select_input_source(receiver, mock_serial):
    await receiver.zone_3.select_input_source(V2015InputSource.TUNER)
    assert b"Z3TUNER\r" in mock_serial.written_data


async def test_zone3_set_volume(receiver, mock_serial):
    await receiver.zone_3.set_volume(-10.0)
    assert b"Z370\r" in mock_serial.written_data


async def test_zone3_mute_on(receiver, mock_serial):
    await receiver.zone_3.mute_on()
    assert b"Z3MUON\r" in mock_serial.written_data


async def test_zone3_mute_off(receiver, mock_serial):
    await receiver.zone_3.mute_off()
    assert b"Z3MUOFF\r" in mock_serial.written_data


# -- Query tests --


async def test_query_power(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("PWSTANDBY")

    task = asyncio.create_task(respond())
    result = await receiver.query_power()
    await task
    assert result is False


async def test_query_volume(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("MVMAX 98")
        mock_serial.inject_response("MVMIN 99")
        mock_serial.inject_response("MV75")

    task = asyncio.create_task(respond())
    result = await receiver.main.query_volume()
    await task
    assert result == -5.0
    assert receiver.state.main_zone.volume_max == 18.0
    assert receiver.state.main_zone.volume_min == -80.0


async def test_query_mute(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("MUOFF")

    task = asyncio.create_task(respond())
    result = await receiver.main.query_mute()
    await task
    assert result is False


async def test_query_main_power(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("ZMON")

    task = asyncio.create_task(respond())
    result = await receiver.main.query_power()
    await task
    assert result is True


async def test_query_input_source(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("SIDVD")

    task = asyncio.create_task(respond())
    result = await receiver.main.query_input_source()
    await task
    assert result == V2015InputSource.DVD


async def test_query_surround_mode(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("MSDOLBY DIGITAL")

    task = asyncio.create_task(respond())
    result = await receiver.main.query_surround_mode()
    await task
    assert result == "DOLBY DIGITAL"


async def test_query_digital_input(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("SDAUTO")

    task = asyncio.create_task(respond())
    result = await receiver.main.query_digital_input()
    await task
    assert result == V2015DigitalInputMode.AUTO


async def test_query_digital_input_no_returns_none(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("SDNO")

    task = asyncio.create_task(respond())
    result = await receiver.main.query_digital_input()
    await task
    assert result is None


async def test_query_video_select(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("SVDVD")

    task = asyncio.create_task(respond())
    result = await receiver.main.query_video_select()
    await task
    assert result == V2015InputSource.DVD


async def test_query_video_select_off_returns_none(receiver, mock_serial):
    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("SVOFF")

    task = asyncio.create_task(respond())
    result = await receiver.main.query_video_select()
    await task
    assert result is None


# -- Event tests: input source --


async def test_input_source_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SIDVD")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.input_source == V2015InputSource.DVD


async def test_input_source_event_with_slash(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SISAT/CBL")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.input_source == V2015InputSource.SAT_CBL


# -- Event tests: surround mode --


async def test_surround_mode_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("MSDIRECT")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.surround_mode == "DIRECT"


async def test_surround_mode_event_combined(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("MSDOLBY DIGITAL")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.surround_mode == "DOLBY DIGITAL"


# -- Event tests: channel volume --


async def test_channel_volume_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("CVFL 52")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.channel_volumes["FL"] == 2.0


async def test_channel_volume_event_subwoofer(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("CVSW 55")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.channel_volumes["SW"] == 5.0


async def test_channel_volume_up_event_no_state_change(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("CVFL UP")
    await asyncio.sleep(0.1)

    assert len(states) == 0


async def test_duplicate_channel_volume_event_no_state_change(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("CVFL 50")
    await asyncio.sleep(0.1)

    assert len(states) == 0


# -- Event tests: parameter settings --


async def test_tone_control_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSTONE CTRL ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.tone_control is True


async def test_bass_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSBAS 53")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.bass == 3


async def test_treble_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSTRE 47")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.treble == -3


async def test_cinema_eq_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSCINEMA EQ.ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.cinema_eq is True


async def test_multeq_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSMULTEQ:FLAT")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.multeq == V2015MultEQ.FLAT


async def test_dynamic_eq_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSDYNEQ ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.dynamic_eq is True


async def test_dynamic_volume_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSDYNVOL NGT")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.dynamic_volume == V2015DynamicVolume.NGT


async def test_drc_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSDRC HI")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.drc == V2015DRC.HI


# -- Event tests: digital input --


async def test_digital_input_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SDANALOG")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.digital_input == V2015DigitalInputMode.ANALOG


async def test_digital_input_no_event(receiver, mock_serial, caplog):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SDNO")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.digital_input is None
    assert "Unknown digital input mode: NO" not in caplog.text


# -- Event tests: audio decode --


async def test_audio_decode_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("DCPCM")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.audio_decode == V2015AudioDecodeMode.PCM


# -- Event tests: video select --


async def test_video_select_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SVCD")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.video_select == V2015InputSource.CD


async def test_video_select_source_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SVSOURCE")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.video_select is None


async def test_video_select_off_event(receiver, mock_serial, caplog):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SVOFF")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.video_select is None
    assert "Unknown video source: OFF" not in caplog.text


# -- Event tests: sleep --


async def test_sleep_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SLP030")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.sleep == "030"


async def test_sleep_off_event(receiver, mock_serial):
    receiver._state.main_zone.sleep = "030"
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SLPOFF")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.sleep is None


# -- Event tests: eco --


async def test_eco_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("ECOON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.eco == V2015EcoMode.ON


async def test_eco_auto_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("ECOAUTO")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.eco == V2015EcoMode.AUTO


# -- Event tests: auto standby --


async def test_auto_standby_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("STBY2H")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.auto_standby == "2H"


async def test_auto_standby_off_event(receiver, mock_serial):
    receiver._state.main_zone.auto_standby = "2H"
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("STBYOFF")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.auto_standby is None


# -- Event tests: dimmer --


async def test_dimmer_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("DIM DIM")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.dimmer == V2015DimmerMode.DIM


async def test_dimmer_off_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("DIM OFF")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.dimmer == V2015DimmerMode.OFF


# -- Event tests: tuner (Marantz TFAN/TPAN/TMAN) --


async def test_tuner_frequency_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("TFAN106000")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.tuner_frequency == "106000"


async def test_tuner_frequency_up_no_state(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("TFANUP")
    await asyncio.sleep(0.1)

    assert len(states) == 0


async def test_tuner_preset_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("TPANB2")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.tuner_preset == "B2"


async def test_tuner_band_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("TMANAM")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.tuner_band == V2015TunerBand.AM


async def test_tuner_mode_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("TMANMANUAL")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.tuner_mode == V2015TunerMode.MANUAL


# -- Event tests: zone 2 --


async def test_zone2_power_on_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2ON")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.power is True


async def test_zone2_power_off_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2ON")
    await asyncio.sleep(0.05)
    mock_serial.inject_response("Z2OFF")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.power is False


async def test_zone2_source_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2DVD")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.input_source == V2015InputSource.DVD


async def test_zone2_volume_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z280")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.volume == 0.0


async def test_zone2_volume_up_no_state(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2UP")
    await asyncio.sleep(0.1)

    assert len(states) == 0


async def test_zone2_mute_on_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2MUON")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.mute is True


async def test_zone2_mute_off_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2MUON")
    await asyncio.sleep(0.05)
    mock_serial.inject_response("Z2MUOFF")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.mute is False


async def test_zone2_source_cancel_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2DVD")
    await asyncio.sleep(0.05)
    mock_serial.inject_response("Z2SOURCE")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.input_source is None


# -- Event tests: zone 3 --


async def test_zone3_power_on_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z3ON")
    await asyncio.sleep(0.1)

    assert states[-1].zone_3.power is True


async def test_zone3_source_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z3TUNER")
    await asyncio.sleep(0.1)

    assert states[-1].zone_3.input_source == V2015InputSource.TUNER


async def test_zone3_sleep_timer_event_ignored(receiver, mock_serial, caplog):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z3SLPOFF")
    await asyncio.sleep(0.1)

    assert len(states) == 0
    assert "Unknown zone source: SLPOFF" not in caplog.text


async def test_zone3_smart_event_ignored(receiver, mock_serial, caplog):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z3SMART1")
    await asyncio.sleep(0.1)

    assert len(states) == 0
    assert "Unknown zone source" not in caplog.text


async def test_zone3_favorite_event_ignored(receiver, mock_serial, caplog):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z3FAVORITE1")
    await asyncio.sleep(0.1)

    assert len(states) == 0
    assert "Unknown zone source" not in caplog.text


async def test_zone3_volume_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z370")
    await asyncio.sleep(0.1)

    assert states[-1].zone_3.volume == -10.0


async def test_zone3_mute_on_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z3MUON")
    await asyncio.sleep(0.1)

    assert states[-1].zone_3.mute is True


# -- Existing event/subscriber tests --


async def test_subscribe_receives_events(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("MV75")
    await asyncio.sleep(0.1)

    assert len(states) == 1
    assert states[0].main_zone.volume == -5.0


async def test_unsubscribe(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    unsub = receiver.subscribe(lambda s: states.append(s))
    unsub()

    mock_serial.inject_response("MV75")
    await asyncio.sleep(0.1)

    assert len(states) == 0


async def test_power_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PWSTANDBY")
    await asyncio.sleep(0.1)

    assert states[-1].power is False


async def test_duplicate_power_event_no_state_change(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PWON")
    await asyncio.sleep(0.1)

    assert len(states) == 0


async def test_mute_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("MUON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.mute is True


async def test_main_zone_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("ZMOFF")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.power is False


async def test_max_volume_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver._state.main_zone.volume_max = None
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("MVMAX 98")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.volume_max == 18.0
    assert states[-1].main_zone.volume == 0.0


async def test_min_volume_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver._state.main_zone.volume_min = None
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("MVMIN 99")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.volume_min == -80.0
    assert states[-1].main_zone.volume == 0.0


async def test_multiple_events(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PWSTANDBY")
    mock_serial.inject_response("MV75")
    mock_serial.inject_response("MUON")
    await asyncio.sleep(0.1)

    assert len(states) == 3
    assert states[-1].power is False
    assert states[-1].main_zone.volume == -5.0
    assert states[-1].main_zone.mute is True


async def test_bad_callback_doesnt_break(receiver, mock_serial):
    def bad_callback(state):
        raise RuntimeError("oops")

    good_states: list[V2015ReceiverState] = []
    receiver.subscribe(bad_callback)
    receiver.subscribe(lambda s: good_states.append(s))

    mock_serial.inject_response("PWSTANDBY")
    await asyncio.sleep(0.1)

    assert len(good_states) == 1


# -- Teardown tests --


async def test_read_error_closes_writer():
    mock = MockSerialConnection()
    recv = await connect_with_defaults(mock)

    assert recv.connected

    mock.reader.set_exception(OSError("device unplugged"))
    await asyncio.sleep(0.1)

    assert not recv.connected
    mock.writer.close.assert_called_once()
    mock.writer.wait_closed.assert_called()


async def test_read_eof_closes_writer():
    mock = MockSerialConnection()
    recv = await connect_with_defaults(mock)

    assert recv.connected

    mock.reader.feed_eof()
    await asyncio.sleep(0.1)

    assert not recv.connected
    mock.writer.close.assert_called_once()
    mock.writer.wait_closed.assert_called()


async def test_write_error_closes_reader():
    mock = MockSerialConnection()
    recv = await connect_with_defaults(mock)

    assert recv.connected
    read_task = recv._read_task

    mock.writer.drain = AsyncMock(side_effect=OSError("device unplugged"))

    with pytest.raises(OSError, match="device unplugged"):
        await recv.power_on()

    assert not recv.connected
    mock.writer.close.assert_called_once()
    assert read_task.cancelled() or read_task.done()


async def test_query_write_error_closes_reader():
    mock = MockSerialConnection()
    recv = await connect_with_defaults(mock)

    assert recv.connected

    mock.writer.drain = AsyncMock(side_effect=OSError("device unplugged"))

    with pytest.raises(OSError, match="device unplugged"):
        await recv.query_power()

    assert not recv.connected
    mock.writer.close.assert_called_once()
    assert len(recv._pending_queries) == 0


async def test_read_error_notifies_none(receiver, mock_serial):
    states = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.reader.set_exception(OSError("device unplugged"))
    await asyncio.sleep(0.1)

    assert states[-1] is None


async def test_read_eof_notifies_none(receiver, mock_serial):
    states = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.reader.feed_eof()
    await asyncio.sleep(0.1)

    assert states[-1] is None


async def test_write_error_notifies_none(receiver, mock_serial):
    states = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.writer.drain = AsyncMock(side_effect=OSError("device unplugged"))

    with pytest.raises(OSError):
        await receiver.power_on()

    assert states[-1] is None


async def test_disconnect_notifies_none(receiver, mock_serial):
    states = []
    receiver.subscribe(lambda s: states.append(s))

    await receiver.disconnect()

    assert states[-1] is None


# ============================================================
# Phase 1: Zone 2/3 extensions + Zone 4
# ============================================================


# -- Zone 2 extended commands --


async def test_zone2_set_sleep(receiver, mock_serial):
    await receiver.zone_2.set_sleep(30)
    assert b"Z2SLP030\r" in mock_serial.written_data


async def test_zone2_sleep_off(receiver, mock_serial):
    await receiver.zone_2.sleep_off()
    assert b"Z2SLPOFF\r" in mock_serial.written_data


async def test_zone2_set_auto_standby(receiver, mock_serial):
    await receiver.zone_2.set_auto_standby("4H")
    assert b"Z2STBY4H\r" in mock_serial.written_data


async def test_zone2_auto_standby_off(receiver, mock_serial):
    await receiver.zone_2.auto_standby_off()
    assert b"Z2STBYOFF\r" in mock_serial.written_data


async def test_zone2_set_channel_mode_stereo(receiver, mock_serial):
    await receiver.zone_2.set_channel_mode(V2015ZoneChannelMode.STEREO)
    assert b"Z2CSST\r" in mock_serial.written_data


async def test_zone2_set_channel_mode_mono(receiver, mock_serial):
    await receiver.zone_2.set_channel_mode(V2015ZoneChannelMode.MONO)
    assert b"Z2CSMONO\r" in mock_serial.written_data


async def test_zone2_channel_volume_up(receiver, mock_serial):
    await receiver.zone_2.channel_volume_up("FL")
    assert b"Z2CVFL UP\r" in mock_serial.written_data


async def test_zone2_set_channel_volume(receiver, mock_serial):
    await receiver.zone_2.set_channel_volume("FR", 3.0)
    assert b"Z2CVFR 53\r" in mock_serial.written_data


async def test_zone2_hpf_on(receiver, mock_serial):
    await receiver.zone_2.hpf_on()
    assert b"Z2HPFON\r" in mock_serial.written_data


async def test_zone2_hpf_off(receiver, mock_serial):
    await receiver.zone_2.hpf_off()
    assert b"Z2HPFOFF\r" in mock_serial.written_data


async def test_zone2_set_bass(receiver, mock_serial):
    await receiver.zone_2.set_bass(3)
    assert b"Z2PSBAS 53\r" in mock_serial.written_data


async def test_zone2_bass_up(receiver, mock_serial):
    await receiver.zone_2.bass_up()
    assert b"Z2PSBAS UP\r" in mock_serial.written_data


async def test_zone2_set_treble(receiver, mock_serial):
    await receiver.zone_2.set_treble(-2)
    assert b"Z2PSTRE 48\r" in mock_serial.written_data


async def test_zone2_treble_down(receiver, mock_serial):
    await receiver.zone_2.treble_down()
    assert b"Z2PSTRE DOWN\r" in mock_serial.written_data


# -- Zone 3 extended commands --


async def test_zone3_set_sleep(receiver, mock_serial):
    await receiver.zone_3.set_sleep(15)
    assert b"Z3SLP015\r" in mock_serial.written_data


async def test_zone3_set_auto_standby(receiver, mock_serial):
    await receiver.zone_3.set_auto_standby("8H")
    assert b"Z3STBY8H\r" in mock_serial.written_data


async def test_zone3_set_channel_mode(receiver, mock_serial):
    await receiver.zone_3.set_channel_mode(V2015ZoneChannelMode.MONO)
    assert b"Z3CSMONO\r" in mock_serial.written_data


async def test_zone3_set_channel_volume(receiver, mock_serial):
    await receiver.zone_3.set_channel_volume("FL", -5.0)
    assert b"Z3CVFL 45\r" in mock_serial.written_data


async def test_zone3_hpf_on(receiver, mock_serial):
    await receiver.zone_3.hpf_on()
    assert b"Z3HPFON\r" in mock_serial.written_data


async def test_zone3_set_bass(receiver, mock_serial):
    await receiver.zone_3.set_bass(5)
    assert b"Z3PSBAS 55\r" in mock_serial.written_data


# -- Zone 4 commands --


async def test_zone4_power_on(receiver, mock_serial):
    await receiver.zone_4.power_on()
    assert b"Z4ON\r" in mock_serial.written_data


async def test_zone4_power_standby(receiver, mock_serial):
    await receiver.zone_4.power_standby()
    assert b"Z4OFF\r" in mock_serial.written_data


async def test_zone4_select_input_source(receiver, mock_serial):
    await receiver.zone_4.select_input_source(V2015InputSource.DVD)
    assert b"Z4DVD\r" in mock_serial.written_data


async def test_zone4_cancel_input_source(receiver, mock_serial):
    await receiver.zone_4.cancel_input_source()
    assert b"Z4SOURCE\r" in mock_serial.written_data


async def test_zone4_set_sleep(receiver, mock_serial):
    await receiver.zone_4.set_sleep(45)
    assert b"Z4SLP045\r" in mock_serial.written_data


async def test_zone4_sleep_off(receiver, mock_serial):
    await receiver.zone_4.sleep_off()
    assert b"Z4SLPOFF\r" in mock_serial.written_data


# -- Zone 2/3/4 event tests --


async def test_zone2_sleep_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2SLP060")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.sleep == "060"


async def test_zone2_sleep_off_event(receiver, mock_serial):
    receiver._state.zone_2.sleep = "030"
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2SLPOFF")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.sleep is None


async def test_zone2_auto_standby_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2STBY4H")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.auto_standby == "4H"


async def test_zone2_channel_mode_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2CSMONO")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.channel_mode == V2015ZoneChannelMode.MONO


async def test_zone2_hpf_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2HPFON")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.hpf is True


async def test_zone2_channel_volume_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2CVFL 52")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.channel_volumes["FL"] == 2.0


async def test_zone2_bass_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2PSBAS 55")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.bass == 5


async def test_zone2_treble_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z2PSTRE 47")
    await asyncio.sleep(0.1)

    assert states[-1].zone_2.treble == -3


async def test_zone3_sleep_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z3SLP120")
    await asyncio.sleep(0.1)

    assert states[-1].zone_3.sleep == "120"


async def test_zone3_channel_mode_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z3CSMONO")
    await asyncio.sleep(0.1)

    assert states[-1].zone_3.channel_mode == V2015ZoneChannelMode.MONO


async def test_zone4_power_on_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z4ON")
    await asyncio.sleep(0.1)

    assert states[-1].zone_4.power is True


async def test_zone4_input_source_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z4BD")
    await asyncio.sleep(0.1)

    assert states[-1].zone_4.input_source == V2015InputSource.BD


async def test_zone4_source_cancel_event(receiver, mock_serial):
    receiver._state.zone_4.input_source = V2015InputSource.BD
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z4SOURCE")
    await asyncio.sleep(0.1)

    assert states[-1].zone_4.input_source is None


async def test_zone4_sleep_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("Z4SLP030")
    await asyncio.sleep(0.1)

    assert states[-1].zone_4.sleep == "030"


# -- Zone 2/3 query tests for new prefixes --


async def test_zone2_query_mute(receiver, mock_serial):
    """Querying Z2MU returns response with prefix Z2MU and matches pending future."""

    async def respond():
        await asyncio.sleep(0.05)
        mock_serial.inject_response("Z2MUOFF")

    task = asyncio.create_task(respond())
    result = await receiver.zone_2.query_mute()
    await task
    assert result is False


# -- Zone 4 state tests --


def test_zone4_initial_state():
    state = V2015Zone4State()
    assert state.power is None
    assert state.input_source is None
    assert state.sleep is None


def test_receiver_state_zone4():
    state = V2015ReceiverState()
    assert state.zone_4.power is None
    state.zone_4.power = True
    copy = state.copy()
    copy.zone_4.power = False
    assert state.zone_4.power is True


# ============================================================
# Phase 2: PS sub-parameters with state
# ============================================================


# -- Subwoofer / Loudness / Dialog Enhancer --


async def test_subwoofer_on(receiver, mock_serial):
    await receiver.main.subwoofer_on()
    assert b"PSSWR ON\r" in mock_serial.written_data


async def test_subwoofer_off(receiver, mock_serial):
    await receiver.main.subwoofer_off()
    assert b"PSSWR OFF\r" in mock_serial.written_data


async def test_loudness_on(receiver, mock_serial):
    await receiver.main.loudness_on()
    assert b"PSLOM ON\r" in mock_serial.written_data


async def test_set_dialog_enhancer(receiver, mock_serial):
    await receiver.main.set_dialog_enhancer(V2015DialogEnhancer.MED)
    assert b"PSDEH MED\r" in mock_serial.written_data


# -- HT-EQ / LFC / V2015MDAX / Audio Delay --


async def test_ht_eq_on(receiver, mock_serial):
    await receiver.main.ht_eq_on()
    assert b"PSHTEQ ON\r" in mock_serial.written_data


async def test_audyssey_lfc_on(receiver, mock_serial):
    await receiver.main.audyssey_lfc_on()
    assert b"PSLFC ON\r" in mock_serial.written_data


async def test_set_mdax(receiver, mock_serial):
    await receiver.main.set_mdax(V2015MDAX.LOW)
    assert b"PSMDAX LOW\r" in mock_serial.written_data


async def test_set_audio_delay(receiver, mock_serial):
    await receiver.main.set_audio_delay(150)
    assert b"PSDELAY 150\r" in mock_serial.written_data


async def test_audio_delay_up(receiver, mock_serial):
    await receiver.main.audio_delay_up()
    assert b"PSDELAY UP\r" in mock_serial.written_data


# -- Neural:X / D.COMP / Bass Sync --


async def test_neural_x_on(receiver, mock_serial):
    await receiver.main.neural_x_on()
    assert b"PSNEURAL ON\r" in mock_serial.written_data


async def test_set_d_comp(receiver, mock_serial):
    await receiver.main.set_d_comp(V2015DComp.LOW)
    assert b"PSDCO LOW\r" in mock_serial.written_data


async def test_set_bass_sync(receiver, mock_serial):
    await receiver.main.set_bass_sync(8)
    assert b"PSBSC 08\r" in mock_serial.written_data


# -- LFE / Reference Level / Graphic / Headphone EQ --


async def test_set_lfe(receiver, mock_serial):
    await receiver.main.set_lfe(-5)
    assert b"PSLFE 05\r" in mock_serial.written_data


async def test_set_lfe_zero(receiver, mock_serial):
    await receiver.main.set_lfe(0)
    assert b"PSLFE 00\r" in mock_serial.written_data


async def test_set_lfe_invalid_raises():
    from marantz_rs232 import MarantzV2015Receiver as MR
    recv = MR("/dev/null")
    with pytest.raises(ValueError):
        await recv.main.set_lfe(5)


async def test_set_reference_level(receiver, mock_serial):
    await receiver.main.set_reference_level(10)
    assert b"PSREFLEV 10\r" in mock_serial.written_data


async def test_set_reference_level_invalid_raises():
    from marantz_rs232 import MarantzV2015Receiver as MR
    recv = MR("/dev/null")
    with pytest.raises(ValueError):
        await recv.main.set_reference_level(7)


async def test_graphic_eq_on(receiver, mock_serial):
    await receiver.main.graphic_eq_on()
    assert b"PSGEQ ON\r" in mock_serial.written_data


async def test_headphone_eq_on(receiver, mock_serial):
    await receiver.main.headphone_eq_on()
    assert b"PSHEQ ON\r" in mock_serial.written_data


# -- PS sub-parameter event tests --


async def test_subwoofer_event(receiver, mock_serial):
    receiver._state.main_zone.subwoofer = False
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSSWR ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.subwoofer is True


async def test_loudness_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSLOM ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.loudness is True


async def test_dialog_enhancer_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSDEH HIGH")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.dialog_enhancer == V2015DialogEnhancer.HIGH


async def test_ht_eq_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSHTEQ ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.ht_eq is True


async def test_audyssey_lfc_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSLFC ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.audyssey_lfc is True


async def test_mdax_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSMDAX HI")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.mdax == V2015MDAX.HI


async def test_audio_delay_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSDELAY 200")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.audio_delay == 200


async def test_neural_x_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSNEURAL ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.neural_x is True


async def test_d_comp_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSDCO MID")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.d_comp == V2015DComp.MID


async def test_bass_sync_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSBSC 08")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.bass_sync == 8


async def test_lfe_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSLFE 05")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.lfe == -5


async def test_reference_level_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSREFLEV 10")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.reference_level == 10


async def test_graphic_eq_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSGEQ ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.graphic_eq is True


async def test_headphone_eq_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("PSHEQ ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.headphone_eq is True


# ============================================================
# Phase 3: Top-level new prefixes (VS, TR, SY, MN, MS smart select)
# ============================================================


# -- VS: HDMI / Video --


async def test_set_aspect(receiver, mock_serial):
    await receiver.main.set_aspect(V2015AspectMode.FULL)
    assert b"VSASPFUL\r" in mock_serial.written_data


async def test_set_hdmi_monitor(receiver, mock_serial):
    await receiver.main.set_hdmi_monitor(V2015HDMIMonitor.MONITOR_1)
    assert b"VSMONI1\r" in mock_serial.written_data


async def test_set_hdmi_audio_output(receiver, mock_serial):
    await receiver.main.set_hdmi_audio_output(V2015HDMIAudioOutput.TV)
    assert b"VSAUDIO TV\r" in mock_serial.written_data


async def test_set_hdmi_resolution(receiver, mock_serial):
    await receiver.main.set_hdmi_resolution(V2015HDMIResolution.K4)
    assert b"VSSC4K\r" in mock_serial.written_data


async def test_set_video_process_mode(receiver, mock_serial):
    await receiver.main.set_video_process_mode(V2015VideoProcessMode.MOVIE)
    assert b"VSVPMMOVI\r" in mock_serial.written_data


async def test_vertical_stretch_on(receiver, mock_serial):
    await receiver.main.vertical_stretch_on()
    assert b"VSVST ON\r" in mock_serial.written_data


# -- VS event tests --


async def test_hdmi_monitor_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("VSMONI2")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.hdmi_monitor == V2015HDMIMonitor.MONITOR_2


async def test_hdmi_audio_output_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("VSAUDIO TV")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.hdmi_audio_output == V2015HDMIAudioOutput.TV


async def test_hdmi_resolution_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("VSSC10P")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.hdmi_resolution == V2015HDMIResolution.P1080


async def test_video_process_mode_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("VSVPMGAME")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.video_process_mode == V2015VideoProcessMode.GAME


# -- TR: Triggers --


async def test_trigger_1_on(receiver, mock_serial):
    await receiver.main.trigger_1_on()
    assert b"TR1 ON\r" in mock_serial.written_data


async def test_trigger_1_off(receiver, mock_serial):
    await receiver.main.trigger_1_off()
    assert b"TR1 OFF\r" in mock_serial.written_data


async def test_trigger_2_on(receiver, mock_serial):
    await receiver.main.trigger_2_on()
    assert b"TR2 ON\r" in mock_serial.written_data


async def test_trigger_1_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("TR1 ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.trigger_1 is True


async def test_trigger_2_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("TR2 ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.trigger_2 is True


# -- SY: Lock --


async def test_remote_lock_on(receiver, mock_serial):
    await receiver.main.remote_lock_on()
    assert b"SYREMOTE LOCK ON\r" in mock_serial.written_data


async def test_remote_lock_off(receiver, mock_serial):
    await receiver.main.remote_lock_off()
    assert b"SYREMOTE LOCK OFF\r" in mock_serial.written_data


async def test_panel_lock_on(receiver, mock_serial):
    await receiver.main.panel_lock_on()
    assert b"SYPANEL LOCK ON\r" in mock_serial.written_data


async def test_panel_lock_with_volume_on(receiver, mock_serial):
    await receiver.main.panel_lock_with_volume_on()
    assert b"SYPANEL+V LOCK ON\r" in mock_serial.written_data


async def test_panel_lock_off(receiver, mock_serial):
    await receiver.main.panel_lock_off()
    assert b"SYPANEL LOCK OFF\r" in mock_serial.written_data


async def test_remote_lock_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SYREMOTE LOCK ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.remote_lock is True


async def test_panel_lock_event(receiver, mock_serial):
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("SYPANEL+V LOCK ON")
    await asyncio.sleep(0.1)

    assert states[-1].main_zone.panel_lock is True


# -- MN: Cursor / Menu --


async def test_cursor_up(receiver, mock_serial):
    await receiver.main.cursor_up()
    assert b"MNCUP\r" in mock_serial.written_data


async def test_cursor_down(receiver, mock_serial):
    await receiver.main.cursor_down()
    assert b"MNCDN\r" in mock_serial.written_data


async def test_cursor_left(receiver, mock_serial):
    await receiver.main.cursor_left()
    assert b"MNCLT\r" in mock_serial.written_data


async def test_cursor_right(receiver, mock_serial):
    await receiver.main.cursor_right()
    assert b"MNCRT\r" in mock_serial.written_data


async def test_enter(receiver, mock_serial):
    await receiver.main.enter()
    assert b"MNENT\r" in mock_serial.written_data


async def test_back(receiver, mock_serial):
    await receiver.main.back()
    assert b"MNRTN\r" in mock_serial.written_data


async def test_menu_on(receiver, mock_serial):
    await receiver.main.menu_on()
    assert b"MNMEN ON\r" in mock_serial.written_data


async def test_menu_off(receiver, mock_serial):
    await receiver.main.menu_off()
    assert b"MNMEN OFF\r" in mock_serial.written_data


async def test_option(receiver, mock_serial):
    await receiver.main.option()
    assert b"MNOPT\r" in mock_serial.written_data


async def test_info(receiver, mock_serial):
    await receiver.main.info()
    assert b"MNINF\r" in mock_serial.written_data


async def test_mn_response_swallowed(receiver, mock_serial, caplog):
    """MN responses should not produce warnings or change state."""
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("MNCUP")
    await asyncio.sleep(0.1)

    assert len(states) == 0


# -- MS: Smart Select --


async def test_smart_select(receiver, mock_serial):
    await receiver.main.smart_select(3)
    assert b"MSSMART3\r" in mock_serial.written_data


async def test_smart_select_memory(receiver, mock_serial):
    await receiver.main.smart_select_memory(2)
    assert b"MSSMART2 MEMORY\r" in mock_serial.written_data


async def test_smart_select_invalid_raises():
    from marantz_rs232 import MarantzV2015Receiver as MR
    recv = MR("/dev/null")
    with pytest.raises(ValueError):
        await recv.main.smart_select(6)


async def test_ms_smart_event_does_not_change_surround(receiver, mock_serial):
    """MSSMART responses should not be parsed as a surround mode."""
    receiver._state.main_zone.surround_mode = "STEREO"
    states: list[V2015ReceiverState] = []
    receiver.subscribe(lambda s: states.append(s))

    mock_serial.inject_response("MSSMART1")
    await asyncio.sleep(0.1)

    assert receiver._state.main_zone.surround_mode == "STEREO"
    assert len(states) == 0


# -- Per-model input map --------------------------------------------------


def test_v2015_supported_inputs_covers_all_models() -> None:
    from marantz_rs232 import V2015_SUPPORTED_INPUTS, V2015InputSource, V2015Model

    for model in V2015Model:
        assert model in V2015_SUPPORTED_INPUTS, model
        inputs = V2015_SUPPORTED_INPUTS[model]
        assert isinstance(inputs, frozenset)
        assert all(isinstance(s, V2015InputSource) for s in inputs)


def test_av8802_and_av8802a_share_input_set() -> None:
    from marantz_rs232 import V2015_SUPPORTED_INPUTS, V2015Model

    assert (
        V2015_SUPPORTED_INPUTS[V2015Model.AV8802]
        == V2015_SUPPORTED_INPUTS[V2015Model.AV8802A]
    )


def test_nr1504_lacks_high_end_inputs() -> None:
    """NR1504 doesn't expose PHONO or HDRADIO."""
    from marantz_rs232 import V2015_SUPPORTED_INPUTS, V2015InputSource, V2015Model

    nr1504 = V2015_SUPPORTED_INPUTS[V2015Model.NR1504]
    assert V2015InputSource.PHONO not in nr1504
    assert V2015InputSource.HDRADIO not in nr1504
    assert V2015InputSource.BD not in nr1504  # NR1504 has no Blu-ray input
