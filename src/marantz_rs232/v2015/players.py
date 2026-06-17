"""Player abstractions for marantz_rs232."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from .const import (
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
    V2015MultEQ,
    V2015TunerBand,
    V2015TunerMode,
    V2015VideoProcessMode,
    V2015ZoneChannelMode,
)
from .protocol import (
    channel_volume_to_param,
    parse_volume_param,
    volume_to_param,
)
from .state import V2015MainZoneState, V2015Zone4State, V2015ZoneState

if TYPE_CHECKING:
    from .receiver import MarantzV2015Receiver


class _BasePlayer:
    """Shared stateful control surface for the main receiver and zones."""

    def __init__(
        self,
        receiver: MarantzV2015Receiver,
        state: V2015ZoneState,
        *,
        power_command: str,
        power_standby_parameter: str,
        input_source_command: str,
        volume_command: str,
    ) -> None:
        self._receiver = receiver
        self._state = state
        self._power_command = power_command
        self._power_standby_parameter = power_standby_parameter
        self._input_source_command = input_source_command
        self._volume_command = volume_command

    @property
    def power(self) -> bool | None:
        return self._state.power

    @property
    def input_source(self) -> V2015InputSource | None:
        return self._state.input_source

    @property
    def volume(self) -> float | None:
        return self._state.volume

    @property
    def volume_min(self) -> float | None:
        return self._receiver._state.main_zone.volume_min

    @property
    def volume_max(self) -> float | None:
        return self._receiver._state.main_zone.volume_max

    async def power_on(self) -> None:
        await self._receiver._send_command(self._power_command, "ON")

    async def power_off(self) -> None:
        await self._receiver._send_command(
            self._power_command,
            self._power_standby_parameter,
        )

    async def select_source(self, source: V2015InputSource) -> None:
        await self._receiver._send_command(
            self._input_source_command,
            source.value,
        )

    async def volume_up(self) -> None:
        await self._receiver._send_command(self._volume_command, "UP")

    async def volume_down(self) -> None:
        await self._receiver._send_command(self._volume_command, "DOWN")

    async def set_volume(self, db: float) -> None:
        await self._receiver._send_command(
            self._volume_command,
            volume_to_param(db),
        )

    async def query_power(self) -> bool:
        resp = await self._receiver._query(self._power_command)
        return resp == "ON"


class V2015MainPlayer(_BasePlayer):
    """Stateful control surface for the receiver's main output."""

    _state: V2015MainZoneState

    def __init__(self, receiver: MarantzV2015Receiver, state: V2015MainZoneState) -> None:
        super().__init__(
            receiver,
            state,
            power_command="ZM",
            power_standby_parameter="OFF",
            input_source_command="SI",
            volume_command="MV",
        )

    @property
    def mute(self) -> bool | None:
        return self._state.mute

    async def mute_on(self) -> None:
        await self._receiver._send_command("MU", "ON")

    async def mute_off(self) -> None:
        await self._receiver._send_command("MU", "OFF")

    async def query_volume(self) -> float:
        resp = await self._receiver._query("MV")
        return parse_volume_param(resp)

    async def channel_volume_up(self, channel: str) -> None:
        await self._receiver._send_command("CV", f"{channel} UP")

    async def channel_volume_down(self, channel: str) -> None:
        await self._receiver._send_command("CV", f"{channel} DOWN")

    async def set_channel_volume(self, channel: str, db: float) -> None:
        await self._receiver._send_command(
            "CV",
            f"{channel} {channel_volume_to_param(db)}",
        )

    async def query_mute(self) -> bool:
        resp = await self._receiver._query("MU")
        return resp == "ON"

    async def query_input_source(self) -> V2015InputSource:
        return V2015InputSource(await self._receiver._query("SI"))

    async def set_surround_mode(self, mode: str) -> None:
        await self._receiver._send_command("MS", mode)

    async def query_surround_mode(self) -> str:
        return await self._receiver._query("MS")

    async def set_digital_input(self, mode: V2015DigitalInputMode) -> None:
        await self._receiver._send_command("SD", mode.value)

    async def query_digital_input(self) -> V2015DigitalInputMode | None:
        param = await self._receiver._query("SD")
        if param == "NO":
            return None
        return V2015DigitalInputMode(param)

    async def set_audio_decode(self, mode: V2015AudioDecodeMode) -> None:
        await self._receiver._send_command("DC", mode.value)

    async def query_audio_decode(self) -> V2015AudioDecodeMode:
        return V2015AudioDecodeMode(await self._receiver._query("DC"))

    async def set_video_select(self, source: V2015InputSource) -> None:
        await self._receiver._send_command("SV", source.value)

    async def cancel_video_select(self) -> None:
        await self._receiver._send_command("SV", "SOURCE")

    async def query_video_select(self) -> V2015InputSource | None:
        param = await self._receiver._query("SV")
        if param in ("SOURCE", "OFF"):
            return None
        return V2015InputSource(param)

    # -- Tone control --

    async def tone_control_on(self) -> None:
        await self._receiver._send_command("PS", "TONE CTRL ON")

    async def tone_control_off(self) -> None:
        await self._receiver._send_command("PS", "TONE CTRL OFF")

    async def set_bass(self, db: int) -> None:
        await self._receiver._send_command("PS", f"BAS {db + 50}")

    async def bass_up(self) -> None:
        await self._receiver._send_command("PS", "BAS UP")

    async def bass_down(self) -> None:
        await self._receiver._send_command("PS", "BAS DOWN")

    async def set_treble(self, db: int) -> None:
        await self._receiver._send_command("PS", f"TRE {db + 50}")

    async def treble_up(self) -> None:
        await self._receiver._send_command("PS", "TRE UP")

    async def treble_down(self) -> None:
        await self._receiver._send_command("PS", "TRE DOWN")

    # -- Audyssey / EQ settings --

    async def cinema_eq_on(self) -> None:
        await self._receiver._send_command("PS", "CINEMA EQ.ON")

    async def cinema_eq_off(self) -> None:
        await self._receiver._send_command("PS", "CINEMA EQ.OFF")

    async def set_multeq(self, mode: V2015MultEQ) -> None:
        await self._receiver._send_command("PS", f"MULTEQ:{mode.value}")

    async def dynamic_eq_on(self) -> None:
        await self._receiver._send_command("PS", "DYNEQ ON")

    async def dynamic_eq_off(self) -> None:
        await self._receiver._send_command("PS", "DYNEQ OFF")

    async def set_dynamic_volume(self, mode: V2015DynamicVolume) -> None:
        await self._receiver._send_command("PS", f"DYNVOL {mode.value}")

    async def set_drc(self, mode: V2015DRC) -> None:
        await self._receiver._send_command("PS", f"DRC {mode.value}")

    # -- Subwoofer / loudness / dialog enhancer --

    async def subwoofer_on(self) -> None:
        await self._receiver._send_command("PS", "SWR ON")

    async def subwoofer_off(self) -> None:
        await self._receiver._send_command("PS", "SWR OFF")

    async def loudness_on(self) -> None:
        await self._receiver._send_command("PS", "LOM ON")

    async def loudness_off(self) -> None:
        await self._receiver._send_command("PS", "LOM OFF")

    async def set_dialog_enhancer(self, mode: V2015DialogEnhancer) -> None:
        await self._receiver._send_command("PS", f"DEH {mode.value}")

    # -- HT-EQ / Audyssey LFC / M-DAX / Audio delay --

    async def ht_eq_on(self) -> None:
        await self._receiver._send_command("PS", "HTEQ ON")

    async def ht_eq_off(self) -> None:
        await self._receiver._send_command("PS", "HTEQ OFF")

    async def audyssey_lfc_on(self) -> None:
        await self._receiver._send_command("PS", "LFC ON")

    async def audyssey_lfc_off(self) -> None:
        await self._receiver._send_command("PS", "LFC OFF")

    async def set_mdax(self, mode: V2015MDAX) -> None:
        await self._receiver._send_command("PS", f"MDAX {mode.value}")

    async def set_audio_delay(self, ms: int) -> None:
        await self._receiver._send_command("PS", f"DELAY {ms:03d}")

    async def audio_delay_up(self) -> None:
        await self._receiver._send_command("PS", "DELAY UP")

    async def audio_delay_down(self) -> None:
        await self._receiver._send_command("PS", "DELAY DOWN")

    # -- Neural:X / D.COMP / Bass Sync --

    async def neural_x_on(self) -> None:
        await self._receiver._send_command("PS", "NEURAL ON")

    async def neural_x_off(self) -> None:
        await self._receiver._send_command("PS", "NEURAL OFF")

    async def set_d_comp(self, mode: V2015DComp) -> None:
        await self._receiver._send_command("PS", f"DCO {mode.value}")

    async def set_bass_sync(self, value: int) -> None:
        await self._receiver._send_command("PS", f"BSC {value:02d}")

    # -- LFE / Reference Level / Graphic / Headphone EQ --

    async def set_lfe(self, db: int) -> None:
        # LFE goes from 0 to -10. Param is 00..10 (absolute value).
        if db > 0 or db < -10:
            raise ValueError("LFE must be between -10 and 0 dB")
        await self._receiver._send_command("PS", f"LFE {abs(db):02d}")

    async def set_reference_level(self, db: int) -> None:
        if db not in (0, 5, 10, 15):
            raise ValueError("Reference level must be 0, 5, 10, or 15")
        await self._receiver._send_command("PS", f"REFLEV {db}")

    async def graphic_eq_on(self) -> None:
        await self._receiver._send_command("PS", "GEQ ON")

    async def graphic_eq_off(self) -> None:
        await self._receiver._send_command("PS", "GEQ OFF")

    async def headphone_eq_on(self) -> None:
        await self._receiver._send_command("PS", "HEQ ON")

    async def headphone_eq_off(self) -> None:
        await self._receiver._send_command("PS", "HEQ OFF")

    # -- Sleep / ECO / Standby / Dimmer --

    async def set_sleep(self, minutes: int) -> None:
        await self._receiver._send_command("SLP", f"{minutes:03d}")

    async def sleep_off(self) -> None:
        await self._receiver._send_command("SLP", "OFF")

    async def set_eco(self, mode: V2015EcoMode) -> None:
        await self._receiver._send_command("ECO", mode.value)

    async def set_auto_standby(self, value: str) -> None:
        await self._receiver._send_command("STBY", value)

    async def auto_standby_off(self) -> None:
        await self._receiver._send_command("STBY", "OFF")

    async def set_dimmer(self, mode: V2015DimmerMode) -> None:
        await self._receiver._send_command("DIM", f" {mode.value}")

    # -- Tuner (Marantz uses TFAN/TPAN/TMAN prefixes) --

    async def tuner_frequency_up(self) -> None:
        await self._receiver._send_command("TFAN", "UP")

    async def tuner_frequency_down(self) -> None:
        await self._receiver._send_command("TFAN", "DOWN")

    async def set_tuner_frequency(self, freq: str) -> None:
        await self._receiver._send_command("TFAN", freq)

    async def query_tuner_frequency(self) -> str:
        return await self._receiver._query("TFAN")

    async def tuner_preset_up(self) -> None:
        await self._receiver._send_command("TPAN", "UP")

    async def tuner_preset_down(self) -> None:
        await self._receiver._send_command("TPAN", "DOWN")

    async def set_tuner_preset(self, preset: str) -> None:
        await self._receiver._send_command("TPAN", preset)

    async def query_tuner_preset(self) -> str:
        return await self._receiver._query("TPAN")

    async def set_tuner_band(self, band: V2015TunerBand) -> None:
        await self._receiver._send_command("TMAN", band.value)

    async def set_tuner_mode(self, mode: V2015TunerMode) -> None:
        await self._receiver._send_command("TMAN", mode.value)

    # -- Video / HDMI settings --

    async def set_aspect(self, mode: V2015AspectMode) -> None:
        await self._receiver._send_command("VS", mode.value)

    async def set_hdmi_monitor(self, mode: V2015HDMIMonitor) -> None:
        await self._receiver._send_command("VS", mode.value)

    async def set_hdmi_audio_output(self, mode: V2015HDMIAudioOutput) -> None:
        await self._receiver._send_command("VS", mode.value)

    async def set_hdmi_resolution(self, resolution: V2015HDMIResolution) -> None:
        await self._receiver._send_command("VS", resolution.value)

    async def set_video_process_mode(self, mode: V2015VideoProcessMode) -> None:
        await self._receiver._send_command("VS", mode.value)

    async def vertical_stretch_on(self) -> None:
        await self._receiver._send_command("VS", "VST ON")

    async def vertical_stretch_off(self) -> None:
        await self._receiver._send_command("VS", "VST OFF")

    # -- Triggers / lock --

    async def trigger_1_on(self) -> None:
        await self._receiver._send_command("TR", "1 ON")

    async def trigger_1_off(self) -> None:
        await self._receiver._send_command("TR", "1 OFF")

    async def trigger_2_on(self) -> None:
        await self._receiver._send_command("TR", "2 ON")

    async def trigger_2_off(self) -> None:
        await self._receiver._send_command("TR", "2 OFF")

    async def remote_lock_on(self) -> None:
        await self._receiver._send_command("SY", "REMOTE LOCK ON")

    async def remote_lock_off(self) -> None:
        await self._receiver._send_command("SY", "REMOTE LOCK OFF")

    async def panel_lock_on(self) -> None:
        await self._receiver._send_command("SY", "PANEL LOCK ON")

    async def panel_lock_with_volume_on(self) -> None:
        await self._receiver._send_command("SY", "PANEL+V LOCK ON")

    async def panel_lock_off(self) -> None:
        await self._receiver._send_command("SY", "PANEL LOCK OFF")

    # -- System control: cursor / menu --

    async def cursor_up(self) -> None:
        await self._receiver._send_command("MN", "CUP")

    async def cursor_down(self) -> None:
        await self._receiver._send_command("MN", "CDN")

    async def cursor_left(self) -> None:
        await self._receiver._send_command("MN", "CLT")

    async def cursor_right(self) -> None:
        await self._receiver._send_command("MN", "CRT")

    async def enter(self) -> None:
        await self._receiver._send_command("MN", "ENT")

    async def back(self) -> None:
        await self._receiver._send_command("MN", "RTN")

    async def menu_on(self) -> None:
        await self._receiver._send_command("MN", "MEN ON")

    async def menu_off(self) -> None:
        await self._receiver._send_command("MN", "MEN OFF")

    async def option(self) -> None:
        await self._receiver._send_command("MN", "OPT")

    async def info(self) -> None:
        await self._receiver._send_command("MN", "INF")

    # -- Smart Select --

    async def smart_select(self, slot: int) -> None:
        if not 1 <= slot <= 5:
            raise ValueError("Smart Select slot must be 1-5")
        await self._receiver._send_command("MS", f"SMART{slot}")

    async def smart_select_memory(self, slot: int) -> None:
        if not 1 <= slot <= 5:
            raise ValueError("Smart Select slot must be 1-5")
        await self._receiver._send_command("MS", f"SMART{slot} MEMORY")


class V2015ZonePlayer(_BasePlayer):
    """Stateful control surface for a Marantz zone (Zone 2 / Zone 3)."""

    def __init__(
        self,
        receiver: MarantzV2015Receiver,
        state: V2015ZoneState,
        *,
        power_command: str,
        power_standby_parameter: str,
        input_source_command: str,
        volume_command: str,
        mute_command: str,
        sleep_command: str,
        auto_standby_command: str,
        channel_mode_command: str,
        channel_volume_command: str,
        hpf_command: str,
        param_command: str,
    ) -> None:
        super().__init__(
            receiver,
            state,
            power_command=power_command,
            power_standby_parameter=power_standby_parameter,
            input_source_command=input_source_command,
            volume_command=volume_command,
        )
        self._mute_command = mute_command
        self._sleep_command = sleep_command
        self._auto_standby_command = auto_standby_command
        self._channel_mode_command = channel_mode_command
        self._channel_volume_command = channel_volume_command
        self._hpf_command = hpf_command
        self._param_command = param_command

    @property
    def mute(self) -> bool | None:
        return self._state.mute

    @property
    def sleep(self) -> str | None:
        return self._state.sleep

    @property
    def auto_standby(self) -> str | None:
        return self._state.auto_standby

    @property
    def channel_mode(self) -> V2015ZoneChannelMode | None:
        return self._state.channel_mode

    @property
    def hpf(self) -> bool | None:
        return self._state.hpf

    @property
    def bass(self) -> float | None:
        return self._state.bass

    @property
    def treble(self) -> float | None:
        return self._state.treble

    async def mute_on(self) -> None:
        await self._receiver._send_command(self._mute_command, "ON")

    async def mute_off(self) -> None:
        await self._receiver._send_command(self._mute_command, "OFF")

    async def query_mute(self) -> bool:
        resp = await self._receiver._query(self._mute_command)
        return resp == "ON"

    # -- Sleep / Auto Standby --

    async def set_sleep(self, minutes: int) -> None:
        await self._receiver._send_command(self._sleep_command, f"{minutes:03d}")

    async def sleep_off(self) -> None:
        await self._receiver._send_command(self._sleep_command, "OFF")

    async def set_auto_standby(self, value: str) -> None:
        await self._receiver._send_command(self._auto_standby_command, value)

    async def auto_standby_off(self) -> None:
        await self._receiver._send_command(self._auto_standby_command, "OFF")

    # -- Stereo / mono --

    async def set_channel_mode(self, mode: V2015ZoneChannelMode) -> None:
        await self._receiver._send_command(self._channel_mode_command, mode.value)

    # -- Channel volume (FL / FR only on zones) --

    async def channel_volume_up(self, channel: str) -> None:
        await self._receiver._send_command(
            self._channel_volume_command, f"{channel} UP"
        )

    async def channel_volume_down(self, channel: str) -> None:
        await self._receiver._send_command(
            self._channel_volume_command, f"{channel} DOWN"
        )

    async def set_channel_volume(self, channel: str, db: float) -> None:
        await self._receiver._send_command(
            self._channel_volume_command,
            f"{channel} {channel_volume_to_param(db)}",
        )

    # -- High Pass Filter --

    async def hpf_on(self) -> None:
        await self._receiver._send_command(self._hpf_command, "ON")

    async def hpf_off(self) -> None:
        await self._receiver._send_command(self._hpf_command, "OFF")

    # -- Bass / Treble --

    async def set_bass(self, db: int) -> None:
        await self._receiver._send_command(self._param_command, f"BAS {db + 50}")

    async def bass_up(self) -> None:
        await self._receiver._send_command(self._param_command, "BAS UP")

    async def bass_down(self) -> None:
        await self._receiver._send_command(self._param_command, "BAS DOWN")

    async def set_treble(self, db: int) -> None:
        await self._receiver._send_command(self._param_command, f"TRE {db + 50}")

    async def treble_up(self) -> None:
        await self._receiver._send_command(self._param_command, "TRE UP")

    async def treble_down(self) -> None:
        await self._receiver._send_command(self._param_command, "TRE DOWN")


class V2015Zone4Player:
    """Control surface for Zone 4 (HDMI passthrough only - no volume/mute)."""

    def __init__(self, receiver: MarantzV2015Receiver, state: V2015Zone4State) -> None:
        self._receiver = receiver
        self._state = state

    @property
    def power(self) -> bool | None:
        return self._state.power

    @property
    def input_source(self) -> V2015InputSource | None:
        return self._state.input_source

    @property
    def sleep(self) -> str | None:
        return self._state.sleep

    async def power_on(self) -> None:
        await self._receiver._send_command("Z4", "ON")

    async def power_off(self) -> None:
        await self._receiver._send_command("Z4", "OFF")

    async def select_source(self, source: V2015InputSource) -> None:
        await self._receiver._send_command("Z4", source.value)

    async def cancel_input_source(self) -> None:
        await self._receiver._send_command("Z4", "SOURCE")

    async def set_sleep(self, minutes: int) -> None:
        await self._receiver._send_command("Z4SLP", f"{minutes:03d}")

    async def sleep_off(self) -> None:
        await self._receiver._send_command("Z4SLP", "OFF")


V2015MarantzPlayer: TypeAlias = V2015MainPlayer | V2015ZonePlayer | V2015Zone4Player
