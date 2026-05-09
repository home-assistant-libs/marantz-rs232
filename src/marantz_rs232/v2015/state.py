"""Runtime state dataclasses for marantz_rs232."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .const import (
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


@dataclass
class V2015ZoneState:
    power: bool | None = None
    input_source: V2015InputSource | None = None
    volume: float | None = None
    mute: bool | None = None
    sleep: str | None = None
    auto_standby: str | None = None
    channel_mode: V2015ZoneChannelMode | None = None
    channel_volumes: dict[str, float] = field(default_factory=dict)
    hpf: bool | None = None
    bass: float | None = None
    treble: float | None = None

    def copy(self) -> V2015ZoneState:
        return replace(self, channel_volumes=dict(self.channel_volumes))


@dataclass
class V2015MainZoneState(V2015ZoneState):
    volume_max: float | None = None
    volume_min: float | None = None
    surround_mode: str | None = None

    digital_input: V2015DigitalInputMode | None = None
    audio_decode: V2015AudioDecodeMode | None = None
    video_select: V2015InputSource | None = None

    tone_control: bool | None = None
    cinema_eq: bool | None = None
    multeq: V2015MultEQ | None = None
    dynamic_eq: bool | None = None
    dynamic_volume: V2015DynamicVolume | None = None
    drc: V2015DRC | None = None

    tuner_frequency: str | None = None
    tuner_preset: str | None = None
    tuner_band: V2015TunerBand | None = None
    tuner_mode: V2015TunerMode | None = None

    eco: V2015EcoMode | None = None
    dimmer: V2015DimmerMode | None = None

    # PS sub-parameters with state
    subwoofer: bool | None = None
    loudness: bool | None = None
    dialog_enhancer: V2015DialogEnhancer | None = None
    ht_eq: bool | None = None
    audyssey_lfc: bool | None = None
    mdax: V2015MDAX | None = None
    audio_delay: int | None = None
    neural_x: bool | None = None
    d_comp: V2015DComp | None = None
    bass_sync: int | None = None
    lfe: int | None = None
    reference_level: int | None = None
    graphic_eq: bool | None = None
    headphone_eq: bool | None = None

    # Video / HDMI settings
    hdmi_monitor: V2015HDMIMonitor | None = None
    hdmi_audio_output: V2015HDMIAudioOutput | None = None
    hdmi_resolution: V2015HDMIResolution | None = None
    video_process_mode: V2015VideoProcessMode | None = None

    # Triggers / lock
    trigger_1: bool | None = None
    trigger_2: bool | None = None
    panel_lock: bool | None = None
    remote_lock: bool | None = None

    def copy(self) -> V2015MainZoneState:
        return replace(self, channel_volumes=dict(self.channel_volumes))


@dataclass
class V2015Zone4State:
    power: bool | None = None
    input_source: V2015InputSource | None = None
    sleep: str | None = None

    def copy(self) -> V2015Zone4State:
        return replace(self)


@dataclass
class V2015ReceiverState:
    power: bool | None = None
    main_zone: V2015MainZoneState = field(default_factory=V2015MainZoneState)
    zone_2: V2015ZoneState = field(default_factory=V2015ZoneState)
    zone_3: V2015ZoneState = field(default_factory=V2015ZoneState)
    zone_4: V2015Zone4State = field(default_factory=V2015Zone4State)

    def copy(self) -> V2015ReceiverState:
        return replace(
            self,
            main_zone=self.main_zone.copy(),
            zone_2=self.zone_2.copy(),
            zone_3=self.zone_3.copy(),
            zone_4=self.zone_4.copy(),
        )
