"""Dataclasses representing observable state of a v2003 receiver."""

from __future__ import annotations

from dataclasses import dataclass, field

from .const import (
    V2003DisplayMode,
    V2003InputMode,
    V2003MultiRoomVolumeMode,
    V2003SamplingFrequency,
    V2003SignalFormat,
    V2003Source,
    V2003SurroundMode,
    V2003TestTone,
    V2003TestToneMode,
    V2003TunerBand,
    V2003TunerMode,
)


@dataclass
class V2003MainState:
    """Main-zone state."""

    power: bool | None = None
    volume: float | None = None  # dB; -inf for muted
    mute: bool | None = None
    attenuator: bool | None = None

    video_input: V2003Source | None = None
    audio_input: V2003Source | None = None
    input_mode: V2003InputMode | None = None
    multi_channel_input: bool | None = None  # MCI on/off

    surround_mode: V2003SurroundMode | None = None
    night_mode: bool | None = None
    re_eq: bool | None = None
    f_direct: bool | None = None

    bass: int | None = None
    treble: int | None = None

    tuner_band: V2003TunerBand | None = None
    tuner_frequency: float | None = None  # MHz for FM, kHz for AM/MW/LW
    tuner_frequency_raw: str | None = None
    tuner_preset: int | None = None
    tuner_mode: V2003TunerMode | None = None

    sleep_minutes: int | None = None
    display: V2003DisplayMode | None = None
    osd: bool | None = None
    menu_visible: bool | None = None
    video_mute: bool | None = None
    test_tone: V2003TestTone | None = None
    test_tone_mode: V2003TestToneMode | None = None

    signal_format: V2003SignalFormat | None = None
    sampling_frequency: V2003SamplingFrequency | None = None
    channel_status_raw: str | None = None  # hex bitfield from ?W


@dataclass
class V2003MultiRoomState:
    """Multi-room (zone 2) state."""

    enabled: bool | None = None  # X0 on / X1 off
    speaker_on: bool | None = None  # ?g
    osd_on: bool | None = None  # ?f
    mute: bool | None = None  # ?h
    volume_mode: V2003MultiRoomVolumeMode | None = None  # ?d
    volume: float | None = None  # dB; -inf for min
    sleep_minutes: int | None = None

    video_input: V2003Source | None = None
    audio_input: V2003Source | None = None
    tuner_band: V2003TunerBand | None = None
    tuner_frequency: float | None = None
    tuner_frequency_raw: str | None = None
    tuner_preset: int | None = None


@dataclass
class V2003ReceiverState:
    """Aggregate state for a v2003 receiver."""

    device_id: str = "1"
    main: V2003MainState = field(default_factory=V2003MainState)
    multi_room: V2003MultiRoomState = field(default_factory=V2003MultiRoomState)
