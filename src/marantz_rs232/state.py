"""Runtime state dataclasses for marantz_rs232."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .const import (
    AudioDecodeMode,
    DComp,
    DialogEnhancer,
    DigitalInputMode,
    DimmerMode,
    DRC,
    DynamicVolume,
    EcoMode,
    HDMIAudioOutput,
    HDMIMonitor,
    HDMIResolution,
    InputSource,
    MDAX,
    MultEQ,
    TunerBand,
    TunerMode,
    VideoProcessMode,
    ZoneChannelMode,
)


@dataclass
class ZoneState:
    power: bool | None = None
    input_source: InputSource | None = None
    volume: float | None = None
    mute: bool | None = None
    sleep: str | None = None
    auto_standby: str | None = None
    channel_mode: ZoneChannelMode | None = None
    channel_volumes: dict[str, float] = field(default_factory=dict)
    hpf: bool | None = None
    bass: float | None = None
    treble: float | None = None

    def copy(self) -> ZoneState:
        return replace(self, channel_volumes=dict(self.channel_volumes))


@dataclass
class MainZoneState(ZoneState):
    volume_max: float | None = None
    volume_min: float | None = None
    surround_mode: str | None = None

    digital_input: DigitalInputMode | None = None
    audio_decode: AudioDecodeMode | None = None
    video_select: InputSource | None = None

    tone_control: bool | None = None
    cinema_eq: bool | None = None
    multeq: MultEQ | None = None
    dynamic_eq: bool | None = None
    dynamic_volume: DynamicVolume | None = None
    drc: DRC | None = None

    tuner_frequency: str | None = None
    tuner_preset: str | None = None
    tuner_band: TunerBand | None = None
    tuner_mode: TunerMode | None = None

    eco: EcoMode | None = None
    dimmer: DimmerMode | None = None

    # PS sub-parameters with state
    subwoofer: bool | None = None
    loudness: bool | None = None
    dialog_enhancer: DialogEnhancer | None = None
    ht_eq: bool | None = None
    audyssey_lfc: bool | None = None
    mdax: MDAX | None = None
    audio_delay: int | None = None
    neural_x: bool | None = None
    d_comp: DComp | None = None
    bass_sync: int | None = None
    lfe: int | None = None
    reference_level: int | None = None
    graphic_eq: bool | None = None
    headphone_eq: bool | None = None

    # Video / HDMI settings
    hdmi_monitor: HDMIMonitor | None = None
    hdmi_audio_output: HDMIAudioOutput | None = None
    hdmi_resolution: HDMIResolution | None = None
    video_process_mode: VideoProcessMode | None = None

    # Triggers / lock
    trigger_1: bool | None = None
    trigger_2: bool | None = None
    panel_lock: bool | None = None
    remote_lock: bool | None = None

    def copy(self) -> MainZoneState:
        return replace(self, channel_volumes=dict(self.channel_volumes))


@dataclass
class Zone4State:
    power: bool | None = None
    input_source: InputSource | None = None
    sleep: str | None = None

    def copy(self) -> Zone4State:
        return replace(self)


@dataclass
class ReceiverState:
    power: bool | None = None
    main_zone: MainZoneState = field(default_factory=MainZoneState)
    zone_2: ZoneState = field(default_factory=ZoneState)
    zone_3: ZoneState = field(default_factory=ZoneState)
    zone_4: Zone4State = field(default_factory=Zone4State)

    def copy(self) -> ReceiverState:
        return replace(
            self,
            main_zone=self.main_zone.copy(),
            zone_2=self.zone_2.copy(),
            zone_3=self.zone_3.copy(),
            zone_4=self.zone_4.copy(),
        )
