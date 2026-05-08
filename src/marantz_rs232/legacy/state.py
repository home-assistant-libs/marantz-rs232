"""Runtime state dataclasses for the legacy (SR7002-era) Marantz protocol."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .const import (
    LegacyDolbyHeadphone,
    LegacyEQMode,
    LegacyHDMIAudioMode,
    LegacyHDMIChannel,
    LegacyInputAD,
    LegacyInputSignal,
    LegacyInputState,
    LegacyIPConverter,
    LegacyMDAX,
    LegacyNightMode,
    LegacySamplingFrequency,
    LegacySignalFormat,
    LegacyStereoMode,
    LegacyTunerMode,
    LegacyVolumeMode,
)


@dataclass
class LegacyMainState:
    """State for the main zone of a legacy Marantz receiver."""

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
    hdmi_channel: LegacyHDMIChannel | None = None  # HDM
    hdmi_audio_mode: LegacyHDMIAudioMode | None = None  # HAM
    ip_converter: LegacyIPConverter | None = None  # IPC
    component2: str | None = None  # CM2 (SR8002 only)

    # Surround / processing
    surround_mode: str | None = None  # single-char status code
    thx_mode: str | None = None  # raw status code (THX_STATUS_NAMES)
    eq_mode: LegacyEQMode | None = None  # EQM
    dolby_headphone_mode: LegacyDolbyHeadphone | None = None  # DHM
    night_mode: LegacyNightMode | None = None  # NGT
    mdax: LegacyMDAX | None = None  # MDA
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
    tuner_mode: LegacyTunerMode | None = None  # TMD
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
    input_ad: LegacyInputAD | None = None  # INP
    input_signal: LegacyInputSignal | None = None  # ISG
    input_state: LegacyInputState | None = None  # IST
    auto_lip_sync: bool | None = None  # ALS (response to HAL query)
    signal_format: LegacySignalFormat | None = None  # SIG
    sampling_frequency: LegacySamplingFrequency | None = None  # SFQ
    channel_status_raw: str | None = None  # CHS

    # Auto status feedback bitmap (set via @AST:F)
    auto_status_layers: str | None = None

    def copy(self) -> LegacyMainState:
        return replace(self)


@dataclass
class LegacyMultiRoomState:
    """State for a multi-room (MR-A or MR-B) zone of a legacy Marantz receiver.

    Multi Room A uses `:` separator on the wire (MPW/MSP/...), Multi Room B
    uses `=` (SR8002 only). Both share this state schema.
    """

    power: bool | None = None  # MPW / MPW=
    speaker_on: bool | None = None  # MSP
    mute: bool | None = None  # MAM (audio mute)
    speaker_mute: bool | None = None  # MSM
    line_volume: float | None = None  # MVL (line out)
    speaker_volume: float | None = None  # MSV
    line_volume_mode: LegacyVolumeMode | None = None  # MVS
    speaker_volume_mode: LegacyVolumeMode | None = None  # MSS
    source_video: str | None = None  # MSC video (always 0 per spec)
    source_audio: str | None = None  # MSC audio
    sleep_minutes: int | None = None  # MSL
    osd_visible: bool | None = None  # MOS
    stereo_mode: LegacyStereoMode | None = None  # MST
    tuner_frequency_raw: str | None = None  # MTF
    tuner_preset: int | None = None  # MTP
    tuner_mode: LegacyTunerMode | None = None  # MTM
    tuner_multicast: int | None = None  # MMC (SR8002 HD only)

    def copy(self) -> LegacyMultiRoomState:
        return replace(self)


@dataclass
class LegacyReceiverState:
    main: LegacyMainState = field(default_factory=LegacyMainState)
    multi_room_a: LegacyMultiRoomState = field(default_factory=LegacyMultiRoomState)
    multi_room_b: LegacyMultiRoomState = field(default_factory=LegacyMultiRoomState)

    @property
    def power(self) -> bool | None:
        return self.main.power

    def copy(self) -> LegacyReceiverState:
        return replace(
            self,
            main=self.main.copy(),
            multi_room_a=self.multi_room_a.copy(),
            multi_room_b=self.multi_room_b.copy(),
        )
