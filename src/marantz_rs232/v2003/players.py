"""Control surfaces for the v2003 (SR9300/SR8300) Marantz protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import (
    SURROUND_COMMAND_CODES,
    V2003Power,
    V2003Source,
    V2003SurroundMode,
)
from .protocol import encode_main_source, encode_multi_source, encode_volume

if TYPE_CHECKING:
    from .receiver import MarantzV2003Receiver


class V2003MainPlayer:
    """Commands targeting the main listening room."""

    def __init__(self, receiver: MarantzV2003Receiver) -> None:
        self._receiver = receiver

    # -- Power --
    async def power_on(self) -> None:
        await self._receiver._send_command(V2003Power.ON.value)

    async def power_off(self) -> None:
        await self._receiver._send_command(V2003Power.OFF.value)

    async def power_toggle(self) -> None:
        await self._receiver._send_command(V2003Power.TOGGLE.value)

    # -- Volume --
    async def volume_up(self) -> None:
        await self._receiver._send_command("G0")

    async def volume_down(self) -> None:
        await self._receiver._send_command("G1")

    async def volume_up_fast(self) -> None:
        await self._receiver._send_command("G2")

    async def volume_down_fast(self) -> None:
        await self._receiver._send_command("G3")

    async def set_volume(self, db: int) -> None:
        """Absolute volume in dB; range -90..+99 integer steps."""
        await self._receiver._send_command(encode_volume(db))

    # -- Mute / attenuator / video mute --
    async def mute_on(self) -> None:
        await self._receiver._send_command("H2")

    async def mute_off(self) -> None:
        await self._receiver._send_command("H1")

    async def attenuator(self) -> None:
        """ATT toggle (no separate on/off command on this protocol)."""
        await self._receiver._send_command("H4")

    async def video_mute(self) -> None:
        """VIDEO MUTE toggle."""
        await self._receiver._send_command("H3")

    # -- Tone (relative steps; no absolute set) --
    async def bass_up(self) -> None:
        await self._receiver._send_command("G4")

    async def bass_down(self) -> None:
        await self._receiver._send_command("G5")

    async def treble_up(self) -> None:
        await self._receiver._send_command("G6")

    async def treble_down(self) -> None:
        await self._receiver._send_command("G7")

    # -- Source select --
    async def select_source(self, source: V2003Source) -> None:
        await self._receiver._send_command(encode_main_source(source))

    async def multi_channel_input_on(self) -> None:
        await self._receiver._send_command("BH")

    async def multi_channel_input_off(self) -> None:
        await self._receiver._send_command("BI")

    async def toggle_input_ad(self) -> None:
        """Toggle digital/analog input mode (A/D button)."""
        await self._receiver._send_command("BJ")

    # -- Surround --
    async def set_surround_mode(self, mode: V2003SurroundMode) -> None:
        """Set the surround mode. Raises ValueError for status-only modes
        (e.g. ``THX_5_1``, ``DTS_MUSIC``, ``MONO``) that the receiver only
        reaches automatically.
        """
        code = SURROUND_COMMAND_CODES.get(mode)
        if code is None:
            raise ValueError(
                f"V2003SurroundMode.{mode.name} is status-only and has no set command"
            )
        await self._receiver._send_command(code)

    async def surround_mode_next(self) -> None:
        await self._receiver._send_command("FX")

    async def surround_mode_prev(self) -> None:
        await self._receiver._send_command("FY")

    # -- Tuner --
    async def auto_tune(self) -> None:
        await self._receiver._send_command("C0")

    async def freq_up(self) -> None:
        await self._receiver._send_command("C1")

    async def freq_down(self) -> None:
        await self._receiver._send_command("C2")

    async def preset_up(self) -> None:
        await self._receiver._send_command("C5")

    async def preset_down(self) -> None:
        await self._receiver._send_command("C6")

    async def preset_scan(self) -> None:
        await self._receiver._send_command("C4")

    async def f_direct(self) -> None:
        """Toggle F-DIRECT (frequency direct entry)."""
        await self._receiver._send_command("C7")

    async def tuner_mode(self) -> None:
        """Toggle T-MODE (auto-stereo / mono)."""
        await self._receiver._send_command("C8")

    async def memo(self) -> None:
        await self._receiver._send_command("D1")

    async def clear(self) -> None:
        await self._receiver._send_command("D0")

    async def direct_key(self, digit: int) -> None:
        if not 0 <= digit <= 9:
            raise ValueError("direct_key digit must be 0..9")
        await self._receiver._send_command(f"E{digit}")

    # -- Sleep / display / OSD / menu --
    async def sleep(self) -> None:
        """Toggle SLEEP (cycles through preset durations)."""
        await self._receiver._send_command("H0")

    async def night_mode(self) -> None:
        """Toggle NIGHT mode."""
        await self._receiver._send_command("J0")

    async def display(self) -> None:
        await self._receiver._send_command("J1")

    async def osd(self) -> None:
        await self._receiver._send_command("J2")

    async def menu(self) -> None:
        await self._receiver._send_command("J3")

    async def menu_off(self) -> None:
        await self._receiver._send_command("J4")

    async def cursor_up(self) -> None:
        await self._receiver._send_command("J5")

    async def cursor_down(self) -> None:
        await self._receiver._send_command("J6")

    async def cursor_left(self) -> None:
        await self._receiver._send_command("J7")

    async def cursor_right(self) -> None:
        await self._receiver._send_command("J8")

    # -- Test tone / re-EQ / volume reset --
    async def test_tone(self) -> None:
        await self._receiver._send_command("I0")

    async def re_eq(self) -> None:
        await self._receiver._send_command("JC")

    async def volume_reset(self) -> None:
        await self._receiver._send_command("JB")


class V2003MultiRoomPlayer:
    """Commands targeting the multi-room (zone 2) output."""

    def __init__(self, receiver: MarantzV2003Receiver) -> None:
        self._receiver = receiver

    # -- Power / state --
    async def on(self) -> None:
        await self._receiver._send_command("L2")

    async def off(self) -> None:
        await self._receiver._send_command("L0")

    async def toggle(self) -> None:
        await self._receiver._send_command("L1")

    async def speaker_on(self) -> None:
        await self._receiver._send_command("N3")

    async def speaker_off(self) -> None:
        await self._receiver._send_command("N4")

    # -- Volume / mute --
    async def mute(self) -> None:
        """Toggle multi-room mute."""
        await self._receiver._send_command("M0")

    async def volume_up(self) -> None:
        await self._receiver._send_command("M1")

    async def volume_down(self) -> None:
        await self._receiver._send_command("M2")

    async def volume_up_fast(self) -> None:
        await self._receiver._send_command("M3")

    async def volume_down_fast(self) -> None:
        await self._receiver._send_command("N0")

    # -- Source select --
    async def select_source(self, source: V2003Source) -> None:
        await self._receiver._send_command(encode_multi_source(source))

    async def sleep(self) -> None:
        await self._receiver._send_command("N1")

    async def multi_channel_input_on(self) -> None:
        await self._receiver._send_command("K1")

    async def multi_channel_input_off(self) -> None:
        await self._receiver._send_command("K2")
