"""Player abstractions for marantz_rs232."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from .const import (
    AudioDecodeMode,
    DigitalInputMode,
    DimmerMode,
    DRC,
    DynamicVolume,
    EcoMode,
    InputSource,
    MultEQ,
    TunerBand,
    TunerMode,
)
from .protocol import (
    channel_volume_to_param,
    parse_volume_param,
    volume_to_param,
)
from .state import MainZoneState, ZoneState

if TYPE_CHECKING:
    from .receiver import MarantzReceiver


class _BasePlayer:
    """Shared stateful control surface for the main receiver and zones."""

    def __init__(
        self,
        receiver: MarantzReceiver,
        state: ZoneState,
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
    def input_source(self) -> InputSource | None:
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

    async def power_standby(self) -> None:
        await self._receiver._send_command(
            self._power_command,
            self._power_standby_parameter,
        )

    async def select_input_source(self, source: InputSource) -> None:
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


class MainPlayer(_BasePlayer):
    """Stateful control surface for the receiver's main output."""

    _state: MainZoneState

    def __init__(self, receiver: MarantzReceiver, state: MainZoneState) -> None:
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

    async def query_input_source(self) -> InputSource:
        return InputSource(await self._receiver._query("SI"))

    async def set_surround_mode(self, mode: str) -> None:
        await self._receiver._send_command("MS", mode)

    async def query_surround_mode(self) -> str:
        return await self._receiver._query("MS")

    async def set_digital_input(self, mode: DigitalInputMode) -> None:
        await self._receiver._send_command("SD", mode.value)

    async def query_digital_input(self) -> DigitalInputMode | None:
        param = await self._receiver._query("SD")
        if param == "NO":
            return None
        return DigitalInputMode(param)

    async def set_audio_decode(self, mode: AudioDecodeMode) -> None:
        await self._receiver._send_command("DC", mode.value)

    async def query_audio_decode(self) -> AudioDecodeMode:
        return AudioDecodeMode(await self._receiver._query("DC"))

    async def set_video_select(self, source: InputSource) -> None:
        await self._receiver._send_command("SV", source.value)

    async def cancel_video_select(self) -> None:
        await self._receiver._send_command("SV", "SOURCE")

    async def query_video_select(self) -> InputSource | None:
        param = await self._receiver._query("SV")
        if param in ("SOURCE", "OFF"):
            return None
        return InputSource(param)

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

    async def set_multeq(self, mode: MultEQ) -> None:
        await self._receiver._send_command("PS", f"MULTEQ:{mode.value}")

    async def dynamic_eq_on(self) -> None:
        await self._receiver._send_command("PS", "DYNEQ ON")

    async def dynamic_eq_off(self) -> None:
        await self._receiver._send_command("PS", "DYNEQ OFF")

    async def set_dynamic_volume(self, mode: DynamicVolume) -> None:
        await self._receiver._send_command("PS", f"DYNVOL {mode.value}")

    async def set_drc(self, mode: DRC) -> None:
        await self._receiver._send_command("PS", f"DRC {mode.value}")

    # -- Sleep / ECO / Standby / Dimmer --

    async def set_sleep(self, minutes: int) -> None:
        await self._receiver._send_command("SLP", f"{minutes:03d}")

    async def sleep_off(self) -> None:
        await self._receiver._send_command("SLP", "OFF")

    async def set_eco(self, mode: EcoMode) -> None:
        await self._receiver._send_command("ECO", mode.value)

    async def set_auto_standby(self, value: str) -> None:
        await self._receiver._send_command("STBY", value)

    async def auto_standby_off(self) -> None:
        await self._receiver._send_command("STBY", "OFF")

    async def set_dimmer(self, mode: DimmerMode) -> None:
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

    async def set_tuner_band(self, band: TunerBand) -> None:
        await self._receiver._send_command("TMAN", band.value)

    async def set_tuner_mode(self, mode: TunerMode) -> None:
        await self._receiver._send_command("TMAN", mode.value)


class ZonePlayer(_BasePlayer):
    """Stateful control surface for a Marantz zone."""

    def __init__(
        self,
        receiver: MarantzReceiver,
        state: ZoneState,
        *,
        power_command: str,
        power_standby_parameter: str,
        input_source_command: str,
        volume_command: str,
        mute_command: str,
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

    @property
    def mute(self) -> bool | None:
        return self._state.mute

    async def mute_on(self) -> None:
        await self._receiver._send_command(self._mute_command, "ON")

    async def mute_off(self) -> None:
        await self._receiver._send_command(self._mute_command, "OFF")

    async def query_mute(self) -> bool:
        resp = await self._receiver._query(self._mute_command)
        return resp == "ON"


MarantzPlayer: TypeAlias = MainPlayer | ZonePlayer
