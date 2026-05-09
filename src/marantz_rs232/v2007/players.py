"""Player abstractions for the legacy (SR7002-era) Marantz protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import (
    V2007Component2,
    V2007Cursor,
    V2007DolbyHeadphone,
    V2007EQMode,
    V2007HDMIAudioMode,
    V2007HDMIChannel,
    V2007IPConverter,
    V2007MDAX,
    V2007Menu,
    V2007NightMode,
    V2007Power,
    V2007Source,
    V2007StereoMode,
    V2007THXSet,
    V2007TriState,
    V2007TunerMode,
    V2007VolumeMode,
)
from .protocol import (
    encode_lip_sync,
    encode_tone,
    encode_tuner_frequency_am_khz,
    encode_tuner_frequency_fm_mhz,
    encode_tuner_xm_channel,
    encode_volume,
    parse_volume,
)
from .state import V2007MainState, V2007MultiRoomState

if TYPE_CHECKING:
    from .receiver import MarantzV2007Receiver


class V2007MainPlayer:
    """Stateful control surface for the main zone of a legacy Marantz receiver."""

    def __init__(
        self, receiver: MarantzV2007Receiver, state: V2007MainState
    ) -> None:
        self._receiver = receiver
        self._state = state

    # ----- Properties -------------------------------------------------------

    @property
    def power(self) -> bool | None:
        return self._state.power

    @property
    def mute(self) -> bool | None:
        return self._state.mute

    @property
    def video_mute(self) -> bool | None:
        return self._state.video_mute

    @property
    def attenuator(self) -> bool | None:
        return self._state.attenuator

    @property
    def seven_one_input(self) -> bool | None:
        return self._state.seven_one_input

    @property
    def volume(self) -> float | None:
        return self._state.volume

    @property
    def bass(self) -> int | None:
        return self._state.bass

    @property
    def treble(self) -> int | None:
        return self._state.treble

    @property
    def source_video(self) -> str | None:
        return self._state.source_video

    @property
    def source_audio(self) -> str | None:
        return self._state.source_audio

    @property
    def speaker_a(self) -> bool | None:
        return self._state.speaker_a

    @property
    def speaker_b(self) -> bool | None:
        return self._state.speaker_b

    @property
    def hdmi_channel(self) -> V2007HDMIChannel | None:
        return self._state.hdmi_channel

    @property
    def hdmi_audio_mode(self) -> V2007HDMIAudioMode | None:
        return self._state.hdmi_audio_mode

    @property
    def ip_converter(self) -> V2007IPConverter | None:
        return self._state.ip_converter

    @property
    def surround_mode(self) -> str | None:
        return self._state.surround_mode

    @property
    def thx_mode(self) -> str | None:
        return self._state.thx_mode

    @property
    def eq_mode(self) -> V2007EQMode | None:
        return self._state.eq_mode

    @property
    def night_mode(self) -> V2007NightMode | None:
        return self._state.night_mode

    @property
    def mdax(self) -> V2007MDAX | None:
        return self._state.mdax

    @property
    def lip_sync_ms(self) -> int | None:
        return self._state.lip_sync_ms

    @property
    def sleep_minutes(self) -> int | None:
        return self._state.sleep_minutes

    @property
    def tuner_frequency_raw(self) -> str | None:
        return self._state.tuner_frequency_raw

    @property
    def tuner_preset(self) -> int | None:
        return self._state.tuner_preset

    @property
    def tuner_mode(self) -> V2007TunerMode | None:
        return self._state.tuner_mode

    # ----- Power -------------------------------------------------------------

    async def power_on(self) -> None:
        await self._receiver._send_command("PWR", V2007Power.ON.value)

    async def power_off(self) -> None:
        await self._receiver._send_command("PWR", V2007Power.OFF.value)

    async def power_toggle(self) -> None:
        await self._receiver._send_command("PWR", V2007Power.TOGGLE.value)

    async def global_power_off(self) -> None:
        await self._receiver._send_command("PWR", V2007Power.GLOBAL_OFF.value)

    async def query_power(self) -> bool:
        resp = await self._receiver._query("PWR")
        return resp == V2007Power.ON.value

    # ----- Mute --------------------------------------------------------------

    async def mute_on(self) -> None:
        await self._receiver._send_command("AMT", V2007TriState.ON.value)

    async def mute_off(self) -> None:
        await self._receiver._send_command("AMT", V2007TriState.OFF.value)

    async def mute_toggle(self) -> None:
        await self._receiver._send_command("AMT", V2007TriState.TOGGLE.value)

    async def query_mute(self) -> bool:
        resp = await self._receiver._query("AMT")
        return resp == V2007TriState.ON.value

    async def video_mute_on(self) -> None:
        await self._receiver._send_command("VMT", V2007TriState.ON.value)

    async def video_mute_off(self) -> None:
        await self._receiver._send_command("VMT", V2007TriState.OFF.value)

    async def video_mute_toggle(self) -> None:
        await self._receiver._send_command("VMT", V2007TriState.TOGGLE.value)

    async def attenuator_on(self) -> None:
        await self._receiver._send_command("ATT", V2007TriState.ON.value)

    async def attenuator_off(self) -> None:
        await self._receiver._send_command("ATT", V2007TriState.OFF.value)

    async def attenuator_toggle(self) -> None:
        await self._receiver._send_command("ATT", V2007TriState.TOGGLE.value)

    async def seven_one_input_on(self) -> None:
        await self._receiver._send_command("71C", V2007TriState.ON.value)

    async def seven_one_input_off(self) -> None:
        await self._receiver._send_command("71C", V2007TriState.OFF.value)

    async def seven_one_input_toggle(self) -> None:
        await self._receiver._send_command("71C", V2007TriState.TOGGLE.value)

    # ----- Volume ------------------------------------------------------------

    async def volume_up(self) -> None:
        await self._receiver._send_command("VOL", "1")

    async def volume_down(self) -> None:
        await self._receiver._send_command("VOL", "2")

    async def volume_up_fast(self) -> None:
        await self._receiver._send_command("VOL", "3")

    async def volume_down_fast(self) -> None:
        await self._receiver._send_command("VOL", "4")

    async def set_volume(self, db: float) -> None:
        await self._receiver._send_command("VOL", f"0{encode_volume(db)}")

    async def query_volume(self) -> float:
        resp = await self._receiver._query("VOL")
        return parse_volume(resp)

    # ----- Tone --------------------------------------------------------------

    async def set_bass(self, db: int) -> None:
        if not -6 <= db <= 6:
            raise ValueError("Bass must be between -6 and +6 dB")
        await self._receiver._send_command("TOB", f"0{encode_tone(db)}")

    async def bass_up(self) -> None:
        await self._receiver._send_command("TOB", "1")

    async def bass_down(self) -> None:
        await self._receiver._send_command("TOB", "2")

    async def set_treble(self, db: int) -> None:
        if not -6 <= db <= 6:
            raise ValueError("Treble must be between -6 and +6 dB")
        await self._receiver._send_command("TOT", f"0{encode_tone(db)}")

    async def treble_up(self) -> None:
        await self._receiver._send_command("TOT", "1")

    async def treble_down(self) -> None:
        await self._receiver._send_command("TOT", "2")

    # ----- Source ------------------------------------------------------------

    async def select_source(self, source: V2007Source | str) -> None:
        code = source.value if isinstance(source, V2007Source) else source
        await self._receiver._send_command("SRC", code)

    async def query_source(self) -> str:
        return await self._receiver._query("SRC")

    # ----- Speaker / HDMI / IP converter -------------------------------------

    async def speaker_cycle(self) -> None:
        await self._receiver._send_command("SPK", "0")

    async def speaker_a_off(self) -> None:
        await self._receiver._send_command("SPK", "1")

    async def speaker_a_on(self) -> None:
        await self._receiver._send_command("SPK", "2")

    async def speaker_b_off(self) -> None:
        await self._receiver._send_command("SPK", "3")

    async def speaker_b_on(self) -> None:
        await self._receiver._send_command("SPK", "4")

    async def set_hdmi_channel(self, channel: V2007HDMIChannel) -> None:
        await self._receiver._send_command("HDM", channel.value)

    async def set_hdmi_audio_mode(self, mode: V2007HDMIAudioMode) -> None:
        await self._receiver._send_command("HAM", mode.value)

    async def set_ip_converter(self, mode: V2007IPConverter) -> None:
        await self._receiver._send_command("IPC", mode.value)

    async def set_component2(self, mode: V2007Component2) -> None:
        """Set component2 routing (SR8002 only)."""
        self._receiver._check_sr8002("Component2 select (CM2)")
        await self._receiver._send_command("CM2", mode.value)

    # ----- Surround / processing --------------------------------------------

    async def set_surround_mode(self, code: str) -> None:
        """Set surround mode by single-char code (see V2007SurroundCode)."""
        await self._receiver._send_command("SUR", f"0{code}")

    async def surround_next(self) -> None:
        await self._receiver._send_command("SUR", "1")

    async def surround_prev(self) -> None:
        await self._receiver._send_command("SUR", "2")

    async def query_surround_mode(self) -> str:
        return await self._receiver._query("SUR")

    async def set_thx_mode(self, mode: V2007THXSet) -> None:
        await self._receiver._send_command("THX", mode.value)

    async def query_thx_mode(self) -> str:
        return await self._receiver._query("THX")

    async def set_eq_mode(self, mode: V2007EQMode) -> None:
        await self._receiver._send_command("EQM", mode.value)

    async def set_dolby_headphone(self, mode: V2007DolbyHeadphone) -> None:
        await self._receiver._send_command("DHM", mode.value)

    async def set_night_mode(self, mode: V2007NightMode) -> None:
        await self._receiver._send_command("NGT", mode.value)

    async def night_mode_toggle(self) -> None:
        await self._receiver._send_command("NGT", V2007NightMode.TOGGLE.value)

    async def set_mdax(self, mode: V2007MDAX) -> None:
        await self._receiver._send_command("MDA", mode.value)

    async def set_lip_sync(self, ms: int) -> None:
        await self._receiver._send_command("LIP", f"0{encode_lip_sync(ms)}")

    async def lip_sync_up(self) -> None:
        await self._receiver._send_command("LIP", "1")

    async def lip_sync_down(self) -> None:
        await self._receiver._send_command("LIP", "2")

    # ----- System / lock / menu ---------------------------------------------

    async def set_sleep(self, minutes: int) -> None:
        if not 0 <= minutes <= 120:
            raise ValueError("Sleep minutes must be between 0 and 120")
        await self._receiver._send_command("SLP", f"0{minutes:03d}")

    async def sleep_off(self) -> None:
        await self._receiver._send_command("SLP", "1")

    async def query_sleep(self) -> int:
        resp = await self._receiver._query("SLP")
        return int(resp)

    async def front_key_lock_on(self) -> None:
        await self._receiver._send_command("FKL", "2")

    async def front_key_lock_off(self) -> None:
        await self._receiver._send_command("FKL", "1")

    async def menu_on(self) -> None:
        await self._receiver._send_command("MNU", V2007Menu.ON.value)

    async def menu_off(self) -> None:
        await self._receiver._send_command("MNU", V2007Menu.OFF.value)

    async def menu_toggle(self) -> None:
        await self._receiver._send_command("MNU", V2007Menu.TOGGLE.value)

    async def menu_enter(self) -> None:
        await self._receiver._send_command("MNU", V2007Menu.ENTER.value)

    async def cursor_up(self) -> None:
        await self._receiver._send_command("CUR", V2007Cursor.UP.value)

    async def cursor_down(self) -> None:
        await self._receiver._send_command("CUR", V2007Cursor.DOWN.value)

    async def cursor_left(self) -> None:
        await self._receiver._send_command("CUR", V2007Cursor.LEFT.value)

    async def cursor_right(self) -> None:
        await self._receiver._send_command("CUR", V2007Cursor.RIGHT.value)

    # ----- DC triggers ------------------------------------------------------

    async def dc_trigger_1_on(self) -> None:
        await self._receiver._send_command("DCT", "12")

    async def dc_trigger_1_off(self) -> None:
        await self._receiver._send_command("DCT", "11")

    async def dc_trigger_2_on(self) -> None:
        await self._receiver._send_command("DCT", "22")

    async def dc_trigger_2_off(self) -> None:
        await self._receiver._send_command("DCT", "21")

    # ----- Test tone --------------------------------------------------------

    async def test_tone_toggle(self) -> None:
        await self._receiver._send_command("TTO", "0")

    async def test_tone_off(self) -> None:
        await self._receiver._send_command("TTO", "1")

    async def test_tone_on(self) -> None:
        await self._receiver._send_command("TTO", "2")

    async def test_tone_next_channel(self) -> None:
        await self._receiver._send_command("TTO", "3")

    async def test_tone_prev_channel(self) -> None:
        await self._receiver._send_command("TTO", "4")

    # ----- Tuner ------------------------------------------------------------

    async def set_tuner_am_frequency(self, khz: int) -> None:
        await self._receiver._send_command(
            "TFQ", f"0{encode_tuner_frequency_am_khz(khz)}"
        )

    async def set_tuner_fm_frequency(self, mhz: float) -> None:
        await self._receiver._send_command(
            "TFQ", f"0{encode_tuner_frequency_fm_mhz(mhz)}"
        )

    async def set_tuner_xm_channel(self, channel: int) -> None:
        await self._receiver._send_command(
            "TFQ", f"0{encode_tuner_xm_channel(channel)}"
        )

    async def tuner_frequency_up(self) -> None:
        await self._receiver._send_command("TFQ", "1")

    async def tuner_frequency_down(self) -> None:
        await self._receiver._send_command("TFQ", "2")

    async def tuner_auto_up(self) -> None:
        await self._receiver._send_command("TFQ", "3")

    async def tuner_auto_down(self) -> None:
        await self._receiver._send_command("TFQ", "4")

    async def tuner_hd_auto_up(self) -> None:
        """HD Radio auto-up (SR8002 only)."""
        self._receiver._check_sr8002("HD Radio tuner auto-up (TFQ:5)")
        await self._receiver._send_command("TFQ", "5")

    async def tuner_hd_auto_down(self) -> None:
        """HD Radio auto-down (SR8002 only)."""
        self._receiver._check_sr8002("HD Radio tuner auto-down (TFQ:6)")
        await self._receiver._send_command("TFQ", "6")

    async def set_tuner_preset(self, preset: int) -> None:
        if not 1 <= preset <= 99:
            raise ValueError("Tuner preset must be 1..99")
        await self._receiver._send_command("TPR", f"0{preset:02d}")

    async def tuner_preset_up(self) -> None:
        await self._receiver._send_command("TPR", "1")

    async def tuner_preset_down(self) -> None:
        await self._receiver._send_command("TPR", "2")

    async def tuner_preset_scan_start(self) -> None:
        await self._receiver._send_command("TPR", "3")

    async def tuner_preset_scan_stop(self) -> None:
        await self._receiver._send_command("TPR", "4")

    async def set_tuner_mode(self, mode: V2007TunerMode) -> None:
        if mode is V2007TunerMode.DIGITAL_AUTO:
            self._receiver._check_sr8002("HD Radio digital-auto tuner mode (TMD:3)")
        await self._receiver._send_command("TMD", mode.value)

    async def tuner_mode_toggle(self) -> None:
        """Cycle tuner mode (mono/auto/HD digital). Wire-form is `@TMD:0`."""
        await self._receiver._send_command("TMD", "0")

    async def tuner_preset_info_on(self) -> None:
        await self._receiver._send_command("TPI", "2")

    async def tuner_preset_info_off(self) -> None:
        await self._receiver._send_command("TPI", "1")

    async def tuner_memorize_preset(self) -> None:
        """Save the current frequency to the active preset slot. Reply: ACK."""
        await self._receiver._send_command("MEM", "0")

    async def tuner_clear_preset(self) -> None:
        """Clear the active preset slot. Reply: ACK."""
        await self._receiver._send_command("CLR", "0")

    # ----- XM category navigation -------------------------------------------

    async def xm_category_toggle(self) -> None:
        await self._receiver._send_command("CAT", "0")

    async def xm_channel_up(self) -> None:
        await self._receiver._send_command("CAT", "1")

    async def xm_channel_down(self) -> None:
        await self._receiver._send_command("CAT", "2")

    async def xm_category_next(self) -> None:
        await self._receiver._send_command("CAT", "3")

    async def xm_category_prev(self) -> None:
        await self._receiver._send_command("CAT", "4")

    # ----- Status-only queries (read-only) ----------------------------------

    async def query_input_ad(self) -> str:
        return await self._receiver._query("INP")

    async def query_input_signal(self) -> str:
        return await self._receiver._query("ISG")

    async def query_input_state(self) -> str:
        return await self._receiver._query("IST")

    async def query_auto_lip_sync(self) -> bool:
        # Query prefix is HAL but the receiver answers with ALS — see spec.
        resp = await self._receiver._query("HAL", response_prefix="ALS")
        return resp == "2"

    async def query_signal_format(self) -> str:
        return await self._receiver._query("SIG")

    async def query_sampling_frequency(self) -> str:
        return await self._receiver._query("SFQ")

    async def query_channel_status(self) -> str:
        return await self._receiver._query("CHS")

    async def query_firmware_version(self) -> str:
        return await self._receiver._query("RSV")

    # ----- Auto status feedback ---------------------------------------------

    async def set_auto_status_feedback(self, layer_mask: int = 0xF) -> None:
        """Enable spontaneous status feedback for the given layer bitmap (0..F)."""
        if not 0 <= layer_mask <= 0xF:
            raise ValueError("layer_mask must be 0..15")
        await self._receiver._send_command("AST", format(layer_mask, "X"))


class V2007MultiRoomPlayer:
    """Stateful control surface for a Multi Room (A or B) zone.

    Multi Room A uses `:` separator; Multi Room B uses `=` (SR8002 only).
    All commands and the state schema are otherwise identical.
    """

    def __init__(
        self,
        receiver: MarantzV2007Receiver,
        state: V2007MultiRoomState,
        *,
        separator: str,
    ) -> None:
        self._receiver = receiver
        self._state = state
        self._separator = separator

    # ----- Properties -------------------------------------------------------

    @property
    def power(self) -> bool | None:
        return self._state.power

    @property
    def speaker_on(self) -> bool | None:
        return self._state.speaker_on

    @property
    def mute(self) -> bool | None:
        return self._state.mute

    @property
    def speaker_mute(self) -> bool | None:
        return self._state.speaker_mute

    @property
    def line_volume(self) -> float | None:
        return self._state.line_volume

    @property
    def speaker_volume(self) -> float | None:
        return self._state.speaker_volume

    @property
    def line_volume_mode(self) -> V2007VolumeMode | None:
        return self._state.line_volume_mode

    @property
    def speaker_volume_mode(self) -> V2007VolumeMode | None:
        return self._state.speaker_volume_mode

    @property
    def source_video(self) -> str | None:
        return self._state.source_video

    @property
    def source_audio(self) -> str | None:
        return self._state.source_audio

    @property
    def stereo_mode(self) -> V2007StereoMode | None:
        return self._state.stereo_mode

    @property
    def sleep_minutes(self) -> int | None:
        return self._state.sleep_minutes

    @property
    def osd_visible(self) -> bool | None:
        return self._state.osd_visible

    # ----- Commands ---------------------------------------------------------

    async def _send(self, prefix: str, payload: str) -> None:
        await self._receiver._send_command(prefix, payload, separator=self._separator)

    async def power_on(self) -> None:
        await self._send("MPW", V2007TriState.ON.value)

    async def power_off(self) -> None:
        await self._send("MPW", V2007TriState.OFF.value)

    async def power_toggle(self) -> None:
        await self._send("MPW", V2007TriState.TOGGLE.value)

    async def speaker_on_command(self) -> None:
        await self._send("MSP", V2007TriState.ON.value)

    async def speaker_off_command(self) -> None:
        await self._send("MSP", V2007TriState.OFF.value)

    async def mute_on(self) -> None:
        await self._send("MAM", V2007TriState.ON.value)

    async def mute_off(self) -> None:
        await self._send("MAM", V2007TriState.OFF.value)

    async def speaker_mute_on(self) -> None:
        await self._send("MSM", V2007TriState.ON.value)

    async def speaker_mute_off(self) -> None:
        await self._send("MSM", V2007TriState.OFF.value)

    async def set_line_volume(self, db: float) -> None:
        await self._send("MVL", f"0{encode_volume(db)}")

    async def line_volume_up(self) -> None:
        await self._send("MVL", "1")

    async def line_volume_down(self) -> None:
        await self._send("MVL", "2")

    async def set_speaker_volume(self, db: float) -> None:
        await self._send("MSV", f"0{encode_volume(db)}")

    async def speaker_volume_up(self) -> None:
        await self._send("MSV", "1")

    async def speaker_volume_down(self) -> None:
        await self._send("MSV", "2")

    async def set_line_volume_mode(self, mode: V2007VolumeMode) -> None:
        await self._send("MVS", mode.value)

    async def set_speaker_volume_mode(self, mode: V2007VolumeMode) -> None:
        await self._send("MSS", mode.value)

    async def select_source(self, source: V2007Source | str) -> None:
        code = source.value if isinstance(source, V2007Source) else source
        await self._send("MSC", code)

    async def set_sleep(self, minutes: int) -> None:
        if not 0 <= minutes <= 120:
            raise ValueError("Sleep minutes must be between 0 and 120")
        await self._send("MSL", f"0{minutes:03d}")

    async def sleep_off(self) -> None:
        await self._send("MSL", "1")

    async def osd_on(self) -> None:
        await self._send("MOS", V2007TriState.ON.value)

    async def osd_off(self) -> None:
        await self._send("MOS", V2007TriState.OFF.value)

    async def set_stereo_mode(self, mode: V2007StereoMode) -> None:
        await self._send("MST", mode.value)

    # Tuner forwarding (Multi Room can drive its own tuner output).

    async def set_tuner_am_frequency(self, khz: int) -> None:
        await self._send("MTF", f"0{encode_tuner_frequency_am_khz(khz)}")

    async def set_tuner_fm_frequency(self, mhz: float) -> None:
        await self._send("MTF", f"0{encode_tuner_frequency_fm_mhz(mhz)}")

    async def tuner_up(self) -> None:
        await self._send("MTF", "1")

    async def tuner_down(self) -> None:
        await self._send("MTF", "2")

    async def set_tuner_preset(self, preset: int) -> None:
        if not 1 <= preset <= 99:
            raise ValueError("Tuner preset must be 1..99")
        await self._send("MTP", f"0{preset:02d}")

    async def set_tuner_mode(self, mode: V2007TunerMode) -> None:
        await self._send("MTM", mode.value)
