"""Runtime state dataclasses for the v2007 (SR7002-era) Marantz protocol."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .const import (
    V2007DolbyHeadphone,
    V2007EQMode,
    V2007HDMIAudioMode,
    V2007HDMIChannel,
    V2007InputAD,
    V2007InputSignal,
    V2007InputState,
    V2007IPConverter,
    V2007MDAX,
    V2007NightMode,
    V2007SamplingFrequency,
    V2007SignalFormat,
    V2007StereoMode,
    V2007TunerMode,
    V2007VolumeMode,
)


@dataclass
class V2007MainState:
    """State for the main zone of a v2007 Marantz receiver."""

    # Power / mute
    power: bool | None = None
    mute: bool | None = None
    video_mute: bool | None = None
    attenuator: bool | None = None  # ATT
    seven_one_input: bool | None = None  # 71C

    # Volume / tone
    volume: float | None = None
    bass: int | None = None  # range -6 to +6 dB
    treble: int | None = None  # range -6 to +6 dB

    # Source / outputs
    source_video: str | None = None  # single-char source code
    source_audio: str | None = None
    speaker_a: bool | None = None  # SPK first char
    speaker_b: bool | None = None  # SPK second char
    hdmi_channel: V2007HDMIChannel | None = None  # HDM
    hdmi_audio_mode: V2007HDMIAudioMode | None = None  # HAM
    ip_converter: V2007IPConverter | None = None  # IPC
    component2: str | None = None  # CM2 (SR8002 only)

    # Surround / processing
    surround_mode: str | None = None  # single-char status code
    thx_mode: str | None = None  # raw status code (V2007_THX_STATUS_NAMES)
    eq_mode: V2007EQMode | None = None  # EQM
    dolby_headphone_mode: V2007DolbyHeadphone | None = None  # DHM
    night_mode: V2007NightMode | None = None  # NGT
    mdax: V2007MDAX | None = None  # MDA
    lip_sync_ms: int | None = None  # LIP

    # System
    sleep_minutes: int | None = None  # SLP
    front_key_lock: bool | None = None  # FKL
    menu_visible: bool | None = None  # MNU (excluding ENTER which is action-only)
    osd_visible: bool | None = None  # OSD (auto-feedback)
    display_on: bool | None = None  # DIP (auto-feedback)
    firmware_version: str | None = None  # RSV

    # DC triggers
    dc_trigger_1: bool | None = None
    dc_trigger_2: bool | None = None

    # Test tone
    test_tone_on: bool | None = None
    test_tone_manual: bool | None = None
    test_tone_channel: int | None = None

    # Tuner (analog SR7002 + HD on SR8002)
    tuner_frequency_raw: str | None = None  # raw TFQ encoded value (5 digits)
    tuner_preset: int | None = None  # TPR
    tuner_mode: V2007TunerMode | None = None  # TMD
    tuner_preset_info: bool | None = None  # TPI
    tuner_multicast: int | None = None  # TMC (SR8002 HD only)

    # XM metadata (read-only)
    xm_category_index: int | None = None  # CAT
    xm_category_searching: bool | None = None  # CAT
    channel_name: str | None = None  # CHN
    artist_name: str | None = None  # ARN
    song_title: str | None = None  # SON
    category_name: str | None = None  # CTN

    # HD Radio metadata (SR8002 only — `*` separator on the wire)
    hd_station_name: str | None = None  # CHN*
    hd_radio_text: str | None = None  # ARN*
    hd_program_service: str | None = None  # SON*
    hd_pty_name: str | None = None  # CTN*

    # Status-only signal info
    input_ad: V2007InputAD | None = None  # INP
    input_signal: V2007InputSignal | None = None  # ISG
    input_state: V2007InputState | None = None  # IST
    auto_lip_sync: bool | None = None  # ALS (response to HAL query)
    signal_format: V2007SignalFormat | None = None  # SIG
    sampling_frequency: V2007SamplingFrequency | None = None  # SFQ
    channel_status_raw: str | None = None  # CHS

    # Auto status feedback bitmap (set via @AST:F)
    auto_status_layers: str | None = None

    def copy(self) -> V2007MainState:
        return replace(self)


@dataclass
class V2007MultiRoomState:
    """State for a multi-room (MR-A or MR-B) zone of a v2007 Marantz receiver.

    Multi Room A uses `:` separator on the wire (MPW/MSP/...), Multi Room B
    uses `=` (SR8002 only). Both share this state schema.
    """

    power: bool | None = None  # MPW / MPW=
    speaker_on: bool | None = None  # MSP
    mute: bool | None = None  # MAM (audio mute)
    speaker_mute: bool | None = None  # MSM
    line_volume: float | None = None  # MVL (line out)
    speaker_volume: float | None = None  # MSV
    line_volume_mode: V2007VolumeMode | None = None  # MVS
    speaker_volume_mode: V2007VolumeMode | None = None  # MSS
    source_video: str | None = None  # MSC video (always 0 per spec)
    source_audio: str | None = None  # MSC audio
    sleep_minutes: int | None = None  # MSL
    osd_visible: bool | None = None  # MOS
    stereo_mode: V2007StereoMode | None = None  # MST
    tuner_frequency_raw: str | None = None  # MTF
    tuner_preset: int | None = None  # MTP
    tuner_mode: V2007TunerMode | None = None  # MTM
    tuner_multicast: int | None = None  # MMC (SR8002 HD only)

    def copy(self) -> V2007MultiRoomState:
        return replace(self)


@dataclass
class V2007ReceiverState:
    main: V2007MainState = field(default_factory=V2007MainState)
    multi_room_a: V2007MultiRoomState = field(default_factory=V2007MultiRoomState)
    multi_room_b: V2007MultiRoomState = field(default_factory=V2007MultiRoomState)

    @property
    def power(self) -> bool | None:
        return self.main.power

    def copy(self) -> V2007ReceiverState:
        return replace(
            self,
            main=self.main.copy(),
            multi_room_a=self.multi_room_a.copy(),
            multi_room_b=self.multi_room_b.copy(),
        )
