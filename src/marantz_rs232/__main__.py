"""CLI to test a Marantz receiver over RS232.

Usage:
    python -m marantz_rs232 /dev/ttyUSB0
    python -m marantz_rs232 /dev/ttyUSB0 --probe
    python -m marantz_rs232 /dev/ttyUSB0 --legacy
    python -m marantz_rs232 /dev/ttyUSB0 --detect
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from . import (
    LegacyModel,
    MarantzLegacyReceiver,
    MarantzReceiver,
    ReceiverState,
    probe,
)
from .legacy import LegacyReceiverState, SOURCE_NAMES, SURROUND_NAMES


def _format_db(db: float | None) -> str:
    if db is None:
        return "?"
    if db == float("-inf") or db == -80.0:
        return "MIN"
    if db >= 0:
        return f"+{db:.1f} dB"
    return f"{db:.1f} dB"


def _format_enum(val: object | None) -> str:
    if val is None:
        return "?"
    value = getattr(val, "value", None)
    if value is not None:
        return str(value)
    return str(val)


def _print_state(state: ReceiverState) -> None:
    print()
    print("=== Receiver Status ===")
    print()

    mz = state.main_zone

    print(
        f"  Power:           {'ON' if state.power else 'STANDBY' if state.power is not None else '?'}"
    )
    print(
        f"  Main zone:       {'ON' if mz.power else 'OFF' if mz.power is not None else '?'}"
    )
    print(f"  Volume:          {_format_db(mz.volume)}")
    print(
        f"  Mute:            {'ON' if mz.mute else 'OFF' if mz.mute is not None else '?'}"
    )
    print(f"  Input source:    {_format_enum(mz.input_source)}")
    print(f"  Surround mode:   {mz.surround_mode or '?'}")
    print(f"  Digital input:   {_format_enum(mz.digital_input)}")
    print(f"  Audio decode:    {_format_enum(mz.audio_decode)}")

    if mz.video_select is not None:
        print(f"  Video select:    {_format_enum(mz.video_select)}")

    ps_lines: list[str] = []
    if mz.tone_control is not None:
        ps_lines.append(f"Tone control {'ON' if mz.tone_control else 'OFF'}")
    if mz.bass is not None:
        ps_lines.append(f"Bass: {mz.bass:+.0f} dB")
    if mz.treble is not None:
        ps_lines.append(f"Treble: {mz.treble:+.0f} dB")
    if mz.cinema_eq is not None:
        ps_lines.append(f"Cinema EQ {'ON' if mz.cinema_eq else 'OFF'}")
    if mz.multeq is not None:
        ps_lines.append(f"MultEQ: {mz.multeq.value}")
    if mz.dynamic_eq is not None:
        ps_lines.append(f"Dynamic EQ {'ON' if mz.dynamic_eq else 'OFF'}")
    if mz.dynamic_volume is not None:
        ps_lines.append(f"Dynamic Volume: {mz.dynamic_volume.value}")
    if mz.drc is not None:
        ps_lines.append(f"DRC: {mz.drc.value}")
    if ps_lines:
        print()
        print("  Parameters:")
        for line in ps_lines:
            print(f"    {line}")

    extra: list[str] = []
    if mz.sleep is not None:
        extra.append(f"Sleep: {mz.sleep} min")
    if mz.eco is not None:
        extra.append(f"ECO: {mz.eco.value}")
    if mz.auto_standby is not None:
        extra.append(f"Auto standby: {mz.auto_standby}")
    if mz.dimmer is not None:
        extra.append(f"Dimmer: {mz.dimmer.value}")
    if extra:
        print()
        print("  System:")
        for line in extra:
            print(f"    {line}")

    if mz.channel_volumes:
        print()
        print("  Channel volumes:")
        for ch, db in sorted(mz.channel_volumes.items()):
            print(f"    {ch:>3s}:  {_format_db(db)}")

    if mz.tuner_frequency or mz.tuner_preset:
        print()
        print("  Tuner:")
        if mz.tuner_band:
            print(f"    Band:       {mz.tuner_band.value}")
        if mz.tuner_frequency:
            print(f"    Frequency:  {mz.tuner_frequency}")
        if mz.tuner_preset:
            print(f"    Preset:     {mz.tuner_preset}")
        if mz.tuner_mode:
            print(f"    Mode:       {mz.tuner_mode.value}")

    for label, zone in [("Zone 2", state.zone_2), ("Zone 3", state.zone_3)]:
        if zone.power is not None:
            print()
            print(f"  {label}:")
            print(f"    Power:   {'ON' if zone.power else 'OFF'}")
            if zone.input_source is not None:
                print(f"    Source:  {zone.input_source.value}")
            if zone.volume is not None:
                print(f"    Volume:  {_format_db(zone.volume)}")
            if zone.mute is not None:
                print(f"    Mute:    {'ON' if zone.mute else 'OFF'}")

    print()


def _print_legacy_state(state: LegacyReceiverState) -> None:
    print()
    print("=== Receiver Status (legacy / SR7002-era) ===")
    print()

    m = state.main

    print(
        f"  Power:           {'ON' if m.power else 'OFF' if m.power is not None else '?'}"
    )
    print(f"  Volume:          {_format_db(m.volume)}")
    print(
        f"  Audio mute:      {'ON' if m.mute else 'OFF' if m.mute is not None else '?'}"
    )
    if m.video_mute is not None:
        print(f"  Video mute:      {'ON' if m.video_mute else 'OFF'}")
    if m.attenuator is not None:
        print(f"  Attenuator:      {'ON' if m.attenuator else 'OFF'}")
    if m.seven_one_input is not None:
        print(f"  7.1 ch input:    {'ON' if m.seven_one_input else 'OFF'}")

    if m.source_video or m.source_audio:
        v = m.source_video or "?"
        a = m.source_audio or "?"
        v_name = SOURCE_NAMES.get(v, "")
        a_name = SOURCE_NAMES.get(a, "")
        print(f"  Source (video):  {v}{f' ({v_name})' if v_name else ''}")
        print(f"  Source (audio):  {a}{f' ({a_name})' if a_name else ''}")

    if m.speaker_a is not None or m.speaker_b is not None:
        print(
            f"  Speakers:        A={'ON' if m.speaker_a else 'OFF'}  B={'ON' if m.speaker_b else 'OFF'}"
        )
    if m.hdmi_channel is not None:
        print(f"  HDMI out:        {m.hdmi_channel.name}")
    if m.hdmi_audio_mode is not None:
        print(f"  HDMI audio:      {m.hdmi_audio_mode.name}")
    if m.ip_converter is not None:
        print(f"  IP converter:    {m.ip_converter.name}")

    if m.surround_mode:
        sur_name = SURROUND_NAMES.get(m.surround_mode, "")
        print(f"  Surround mode:   {m.surround_mode}{f' ({sur_name})' if sur_name else ''}")
    if m.thx_mode is not None:
        from .legacy import THX_STATUS_NAMES

        thx_name = THX_STATUS_NAMES.get(m.thx_mode, "")
        print(f"  THX mode:        {m.thx_mode}{f' ({thx_name})' if thx_name else ''}")
    if m.eq_mode is not None:
        print(f"  EQ mode:         {m.eq_mode.name}")
    if m.night_mode is not None:
        print(f"  Night mode:      {m.night_mode.name}")
    if m.mdax is not None:
        print(f"  M-DAX:           {m.mdax.name}")
    if m.dolby_headphone_mode is not None:
        print(f"  Dolby HP mode:   {m.dolby_headphone_mode.name}")
    if m.lip_sync_ms is not None:
        print(f"  Lip sync:        {m.lip_sync_ms} ms")

    if m.bass is not None:
        print(f"  Bass:            {m.bass:+d} dB")
    if m.treble is not None:
        print(f"  Treble:          {m.treble:+d} dB")

    if (
        m.tuner_frequency_raw
        or m.tuner_preset is not None
        or m.tuner_mode is not None
    ):
        print()
        print("  Tuner:")
        if m.tuner_frequency_raw:
            try:
                from .legacy.protocol import decode_tuner_frequency

                band, value = decode_tuner_frequency(m.tuner_frequency_raw)
                if band == "FM":
                    print(f"    Frequency:    FM {value:.2f} MHz")
                elif band == "AM":
                    print(f"    Frequency:    AM {int(value)} kHz")
                else:
                    print(f"    Frequency:    XM ch {int(value)}")
            except Exception:
                print(f"    Frequency raw: {m.tuner_frequency_raw}")
        if m.tuner_preset is not None:
            print(f"    Preset:       {m.tuner_preset}")
        if m.tuner_mode is not None:
            print(f"    Mode:         {m.tuner_mode.name}")

    extras: list[str] = []
    if m.input_ad is not None:
        extras.append(f"INP: {m.input_ad.name}")
    if m.input_signal is not None:
        extras.append(f"ISG: {m.input_signal.name}")
    if m.input_state is not None:
        extras.append(f"IST: {m.input_state.name}")
    if m.signal_format is not None:
        extras.append(f"SIG: {m.signal_format.name}")
    if m.sampling_frequency is not None:
        extras.append(f"SFQ: {m.sampling_frequency.name}")
    if m.firmware_version is not None:
        extras.append(f"firmware: {m.firmware_version}")
    if extras:
        print()
        print("  Signal info:")
        for line in extras:
            print(f"    {line}")

    triggers: list[str] = []
    if m.dc_trigger_1 is not None:
        triggers.append(f"DC1={'ON' if m.dc_trigger_1 else 'OFF'}")
    if m.dc_trigger_2 is not None:
        triggers.append(f"DC2={'ON' if m.dc_trigger_2 else 'OFF'}")
    if triggers:
        print(f"  Triggers:        {' '.join(triggers)}")

    if m.sleep_minutes is not None:
        print(
            f"  Sleep:           {f'{m.sleep_minutes} min' if m.sleep_minutes else 'OFF'}"
        )
    if m.front_key_lock is not None:
        print(f"  Front key lock:  {'ON' if m.front_key_lock else 'OFF'}")

    a = state.multi_room_a
    if a.power is not None or a.line_volume is not None:
        print()
        print("  Multi Room A:")
        if a.power is not None:
            print(f"    Power:        {'ON' if a.power else 'OFF'}")
        if a.line_volume is not None:
            print(f"    Line vol:     {_format_db(a.line_volume)}")
        if a.source_audio is not None:
            print(
                f"    Source audio: {a.source_audio} ({SOURCE_NAMES.get(a.source_audio, '?')})"
            )
        if a.mute is not None:
            print(f"    Mute:         {'ON' if a.mute else 'OFF'}")

    print()


async def _run_modern(port: str, probe_sources: bool) -> None:
    receiver = MarantzReceiver(port)

    print(f"Connecting to {port}...")
    try:
        await receiver.connect()
        print("Querying receiver state...")
        await receiver.query_state()
    except ConnectionError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    try:
        _print_state(receiver.state)

        if probe_sources:
            print("Probing input sources (this will briefly switch inputs)...")
            print()
            sources = await receiver.probe_sources()
            print(f"Available sources ({len(sources)}):")
            for source in sorted(sources, key=lambda s: s.value):
                print(f"  - {source.value}")
            print()
    finally:
        await receiver.disconnect()


async def _run_legacy(port: str, model: LegacyModel = LegacyModel.GENERIC) -> None:
    receiver = MarantzLegacyReceiver(port, model=model)

    print(f"Connecting to {port} (legacy protocol, model={model.value})...")
    try:
        await receiver.connect()
        print("Querying receiver state...")
        await receiver.query_state()
    except ConnectionError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    try:
        _print_legacy_state(receiver.state)
    finally:
        await receiver.disconnect()


async def _run(
    port: str,
    probe_sources: bool,
    legacy: bool,
    detect: bool,
    legacy_model: LegacyModel,
) -> None:
    if detect:
        print(f"Probing protocol on {port}...")
        try:
            cls = await probe(port)
        except ConnectionError as err:
            print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)
        print(f"Detected: {cls.__name__}")
        if cls is MarantzLegacyReceiver:
            await _run_legacy(port, legacy_model)
            return
        await _run_modern(port, probe_sources)
        return

    if legacy:
        await _run_legacy(port, legacy_model)
        return

    await _run_modern(port, probe_sources)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test a Marantz receiver over RS232",
    )
    parser.add_argument("port", help="Serial port (e.g. /dev/ttyUSB0)")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Probe available input sources (modern protocol only)",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use the legacy SR7002-era @CMD: protocol",
    )
    parser.add_argument(
        "--detect",
        action="store_true",
        help="Auto-detect which protocol the receiver speaks before connecting",
    )
    parser.add_argument(
        "--model",
        choices=[m.value for m in LegacyModel],
        default=LegacyModel.GENERIC.value,
        help=(
            "Specific legacy model. Picks generic baseline by default; "
            "select SR8002 to silence warnings about Multi Room B / HD Radio "
            "extensions and unlock those features."
        ),
    )
    args = parser.parse_args()

    if args.legacy and args.detect:
        parser.error("--legacy and --detect are mutually exclusive")

    asyncio.run(
        _run(
            args.port,
            args.probe,
            args.legacy,
            args.detect,
            LegacyModel(args.model),
        )
    )


if __name__ == "__main__":
    main()
