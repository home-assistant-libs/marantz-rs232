"""Runtime state dataclasses for marantz_rs232."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

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


@dataclass
class ZoneState:
    power: bool | None = None
    input_source: InputSource | None = None
    volume: float | None = None
    mute: bool | None = None

    def copy(self) -> ZoneState:
        return replace(self)


@dataclass
class MainZoneState(ZoneState):
    volume_max: float | None = None
    volume_min: float | None = None
    surround_mode: str | None = None
    channel_volumes: dict[str, float] = field(default_factory=dict)

    digital_input: DigitalInputMode | None = None
    audio_decode: AudioDecodeMode | None = None
    video_select: InputSource | None = None

    tone_control: bool | None = None
    bass: float | None = None
    treble: float | None = None
    cinema_eq: bool | None = None
    multeq: MultEQ | None = None
    dynamic_eq: bool | None = None
    dynamic_volume: DynamicVolume | None = None
    drc: DRC | None = None

    tuner_frequency: str | None = None
    tuner_preset: str | None = None
    tuner_band: TunerBand | None = None
    tuner_mode: TunerMode | None = None

    sleep: str | None = None
    eco: EcoMode | None = None
    auto_standby: str | None = None
    dimmer: DimmerMode | None = None

    def copy(self) -> MainZoneState:
        return replace(self, channel_volumes=dict(self.channel_volumes))


@dataclass
class ReceiverState:
    power: bool | None = None
    main_zone: MainZoneState = field(default_factory=MainZoneState)
    zone_2: ZoneState = field(default_factory=ZoneState)
    zone_3: ZoneState = field(default_factory=ZoneState)

    def copy(self) -> ReceiverState:
        return replace(
            self,
            main_zone=self.main_zone.copy(),
            zone_2=replace(self.zone_2),
            zone_3=replace(self.zone_3),
        )
