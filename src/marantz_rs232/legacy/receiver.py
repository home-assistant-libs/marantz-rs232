"""Receiver implementation for the legacy (SR7002-era) Marantz protocol."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import serialx

from .const import (
    LEGACY_BAUD_RATE,
    LEGACY_COMMAND_TIMEOUT,
    LEGACY_TERMINATOR,
    LegacyDolbyHeadphone,
    LegacyEQMode,
    LegacyHDMIAudioMode,
    LegacyHDMIChannel,
    LegacyInputAD,
    LegacyInputSignal,
    LegacyInputState,
    LegacyIPConverter,
    LegacyMDAX,
    LegacyModel,
    LegacyNightMode,
    LegacyPower,
    LegacySamplingFrequency,
    LegacySignalFormat,
    LegacyStereoMode,
    LegacyTriState,
    LegacyTunerMode,
    LegacyVolumeMode,
)
from .players import LegacyMainPlayer, LegacyMultiRoomPlayer
from .protocol import (
    PendingQuery,
    decode_tuner_frequency,
    encode_query,
    encode_query_b,
    encode_set_command,
    encode_set_command_b,
    parse_line,
    parse_tone,
    parse_volume,
)
from .state import (
    LegacyMainState,
    LegacyMultiRoomState,
    LegacyReceiverState,
)

_LOGGER = logging.getLogger(__name__)


StateCallback = Callable[[LegacyReceiverState | None], None]


_MAIN_QUERY_PREFIXES = (
    "PWR",
    "ATT",
    "AMT",
    "VMT",
    "VOL",
    "TOB",
    "TOT",
    "SRC",
    "71C",
    "SPK",
    "HDM",
    "HAM",
    "IPC",
    "SLP",
    "MNU",
    "DCT",
    "FKL",
    "SUR",
    "THX",
    "EQM",
    "DHM",
    "NGT",
    "MDA",
    "LIP",
    "TTO",
    "TFQ",
    "TPR",
    "TMD",
    "TPI",
    "INP",
    "ISG",
    "IST",
    "SIG",
    "SFQ",
    "CHS",
    "RSV",
)

# Multi Room A query prefixes (`:` separator). Skip the read-only ones unless
# the caller asks via query_xm() / query_hd_radio_metadata().
_MR_A_QUERY_PREFIXES = (
    "MPW",
    "MSP",
    "MAM",
    "MSM",
    "MVL",
    "MSV",
    "MVS",
    "MSS",
    "MSC",
    "MSL",
    "MOS",
    "MST",
    "MTF",
    "MTP",
    "MTM",
)

# Multi Room B uses the same prefixes but with `=` separator (SR8002 only).
_MR_B_QUERY_PREFIXES = _MR_A_QUERY_PREFIXES

# Prefixes that route to a multi-room state (rather than the main zone), when
# delivered with the `:` separator.
_MULTI_ROOM_PREFIXES = frozenset(_MR_A_QUERY_PREFIXES + ("MMC",))


# ----- Two-character tri-state mapping helpers ------------------------------


def _tristate_to_bool(value: str) -> bool | None:
    if value == LegacyTriState.ON.value:
        return True
    if value == LegacyTriState.OFF.value:
        return False
    return None


# ----------------------------------------------------------------------------


class MarantzLegacyReceiver:
    """Async controller for a Marantz receiver speaking the SR7002-era protocol."""

    def __init__(
        self, port: str, *, model: LegacyModel = LegacyModel.GENERIC
    ) -> None:
        self._port = port
        self._model = model
        self._reader: asyncio.StreamReader | None = None
        self._writer: serialx.SerialStreamWriter | None = None
        self._read_task: asyncio.Task | None = None
        self._state = LegacyReceiverState()
        self.main = LegacyMainPlayer(self, self._state.main)
        self.multi_room_a = LegacyMultiRoomPlayer(
            self, self._state.multi_room_a, separator=":"
        )
        # Multi Room B is SR8002-only — instantiating on other models still
        # works but the receiver will ignore commands.
        self.multi_room_b = LegacyMultiRoomPlayer(
            self, self._state.multi_room_b, separator="="
        )
        self._subscribers: list[StateCallback] = []
        self._pending_queries: list[PendingQuery] = []
        self._write_lock = asyncio.Lock()
        self._connected = False

    @property
    def model(self) -> LegacyModel:
        return self._model

    @property
    def state(self) -> LegacyReceiverState:
        return self._state.copy()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def power(self) -> bool | None:
        return self._state.main.power

    def subscribe(self, callback: StateCallback) -> Callable[[], None]:
        self._subscribers.append(callback)
        return lambda: self._subscribers.remove(callback)

    async def connect(self) -> None:
        self._reader, self._writer = await serialx.open_serial_connection(
            self._port,
            baudrate=LEGACY_BAUD_RATE,
        )
        self._connected = True
        self._read_task = asyncio.create_task(self._read_loop())

        try:
            await self._query("PWR")
        except TimeoutError:
            await self.disconnect()
            raise ConnectionError(
                f"No response from receiver on {self._port}"
            ) from None

        # Enable auto status feedback (all four layers) so subscribers see
        # spontaneous state changes.
        try:
            await self._send_command("AST", "F")
        except Exception:
            _LOGGER.warning("Failed to enable auto status feedback", exc_info=True)

        _LOGGER.info(
            "Connected to legacy Marantz receiver on %s (model=%s)",
            self._port,
            self._model.value,
        )

    async def disconnect(self) -> None:
        await self._teardown()
        _LOGGER.info("Disconnected from legacy Marantz receiver")

    async def query_state(self) -> None:
        """Query each documented prefix to refresh the main-zone `state`."""
        for prefix in _MAIN_QUERY_PREFIXES:
            try:
                await self._query(prefix)
            except TimeoutError:
                _LOGGER.debug("Query timed out for %s", prefix)

    async def query_multi_room_a(self) -> None:
        """Query Multi Room A (`:` separator) state. SR8002 only on some models."""
        for prefix in _MR_A_QUERY_PREFIXES:
            try:
                await self._query(prefix)
            except TimeoutError:
                _LOGGER.debug("MR-A query timed out for %s", prefix)

    async def query_multi_room_b(self) -> None:
        """Query Multi Room B (`=` separator) state. SR8002 only."""
        if self._model is not LegacyModel.SR8002:
            _LOGGER.warning(
                "Querying Multi Room B but model is %s; SR8002-only feature",
                self._model.value,
            )
        for prefix in _MR_B_QUERY_PREFIXES:
            try:
                await self._query(prefix, separator="=")
            except TimeoutError:
                _LOGGER.debug("MR-B query timed out for %s", prefix)

    async def query_hd_radio_metadata(self) -> None:
        """Query HD Radio metadata (`*` separator). SR8002 only."""
        if self._model is not LegacyModel.SR8002:
            _LOGGER.warning(
                "Querying HD Radio metadata but model is %s; SR8002-only feature",
                self._model.value,
            )
        for prefix in ("CHN", "ARN", "SON", "CTN"):
            try:
                await self._query(prefix, separator="*")
            except TimeoutError:
                _LOGGER.debug("HD Radio query timed out for %s", prefix)

    async def _send_command(
        self, prefix: str, payload: str, *, separator: str = ":"
    ) -> None:
        assert self._writer is not None
        if separator == "=":
            msg = encode_set_command_b(prefix, payload)
        else:
            msg = encode_set_command(prefix, payload)
        _LOGGER.debug("Sending: %s", msg)
        try:
            async with self._write_lock:
                self._writer.write(msg)
                await self._writer.drain()
        except Exception:
            _LOGGER.exception("Error writing to serial port")
            await self._teardown()
            raise

    async def _query(
        self,
        prefix: str,
        *,
        separator: str = ":",
        response_prefix: str | None = None,
    ) -> str:
        assert self._writer is not None
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        # `response_prefix` lets queries like `@HAL:?` listen for a response
        # under a different prefix (`ALS`) per the spec's intentional asymmetry.
        pending = PendingQuery(
            prefix=response_prefix or prefix,
            future=future,
            separator=separator,
        )
        self._pending_queries.append(pending)

        try:
            if separator == "=":
                msg = encode_query_b(prefix)
            elif separator == "*":
                msg = f"@{prefix}*?\r".encode("ascii")
            else:
                msg = encode_query(prefix)
            _LOGGER.debug("Querying: %s", msg)
            try:
                async with self._write_lock:
                    self._writer.write(msg)
                    await self._writer.drain()
            except Exception:
                _LOGGER.exception("Error writing to serial port")
                await self._teardown()
                raise
            return await asyncio.wait_for(future, timeout=LEGACY_COMMAND_TIMEOUT)
        finally:
            if pending in self._pending_queries:
                self._pending_queries.remove(pending)

    async def _teardown(self) -> None:
        if not self._connected:
            return
        self._connected = False

        current = asyncio.current_task()

        if self._read_task is not None and self._read_task is not current:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        self._read_task = None

        if self._writer is not None:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None

        self._notify_subscribers()

    async def _read_loop(self) -> None:
        assert self._reader is not None
        buf = b""

        while self._connected:
            try:
                data = await self._reader.read(256)
            except Exception:
                if not self._connected:
                    return
                _LOGGER.exception("Error reading from serial port")
                await self._teardown()
                return

            if not data:
                _LOGGER.warning("Serial connection closed")
                await self._teardown()
                return

            buf += data

            while LEGACY_TERMINATOR in buf:
                line, buf = buf.split(LEGACY_TERMINATOR, 1)
                if not line:
                    continue
                if line.startswith(b"\n"):
                    line = line[1:]
                if not line:
                    continue
                try:
                    text = line.decode("ascii", errors="replace")
                except Exception:
                    continue
                self._process_line(text)

    def _process_line(self, line: str) -> None:
        _LOGGER.debug("Received: %s", line)

        parsed = parse_line(line)
        if parsed is None:
            return
        prefix, separator, value = parsed

        changed = self._dispatch(prefix, separator, value)

        for pending in list(self._pending_queries):
            if (
                pending.prefix == prefix
                and pending.separator == separator
                and not pending.future.done()
            ):
                pending.future.set_result(value)

        if changed:
            self._notify_subscribers()

    @staticmethod
    def _set_attr(target: object, attr: str, new_value: object) -> bool:
        if getattr(target, attr) == new_value:
            return False
        setattr(target, attr, new_value)
        return True

    # ----- Dispatch -----------------------------------------------------------

    def _dispatch(self, prefix: str, separator: str, value: str) -> bool:
        # Multi Room B uses `=`; HD Radio uses `*`.
        if separator == "=":
            return self._apply_multiroom(self._state.multi_room_b, prefix, value)
        if separator == "*":
            return self._apply_hd_radio(prefix, value)

        # Main-zone vs Multi Room A is determined by prefix family.
        if prefix in _MULTI_ROOM_PREFIXES:
            return self._apply_multiroom(self._state.multi_room_a, prefix, value)

        return self._apply_main(prefix, value)

    # ----- Main zone ----------------------------------------------------------

    def _apply_main(self, prefix: str, value: str) -> bool:
        main = self._state.main

        if prefix == "PWR":
            if value == LegacyPower.ON.value:
                return self._set_attr(main, "power", True)
            if value == LegacyPower.OFF.value:
                return self._set_attr(main, "power", False)
            return False

        if prefix == "AMT":
            return self._set_attr(main, "mute", _tristate_to_bool(value))

        if prefix == "VMT":
            return self._set_attr(main, "video_mute", _tristate_to_bool(value))

        if prefix == "ATT":
            return self._set_attr(main, "attenuator", _tristate_to_bool(value))

        if prefix == "71C":
            return self._set_attr(main, "seven_one_input", _tristate_to_bool(value))

        if prefix == "VOL":
            try:
                return self._set_attr(main, "volume", parse_volume(value))
            except (ValueError, IndexError):
                _LOGGER.warning("Could not parse VOL value: %s", value)
                return False

        if prefix == "TOB":
            try:
                return self._set_attr(main, "bass", parse_tone(value))
            except ValueError:
                return False

        if prefix == "TOT":
            try:
                return self._set_attr(main, "treble", parse_tone(value))
            except ValueError:
                return False

        if prefix == "SRC":
            changed = False
            if len(value) >= 1:
                changed = self._set_attr(main, "source_video", value[0])
            if len(value) >= 2:
                changed = self._set_attr(main, "source_audio", value[1]) or changed
            return changed

        if prefix == "SPK":
            # Status `SPK:ab` where a/b are 1=OFF/2=ON.
            changed = False
            if len(value) >= 1:
                changed = self._set_attr(main, "speaker_a", value[0] == "2")
            if len(value) >= 2:
                changed = (
                    self._set_attr(main, "speaker_b", value[1] == "2") or changed
                )
            return changed

        if prefix == "HDM":
            try:
                return self._set_attr(
                    main, "hdmi_channel", LegacyHDMIChannel(value)
                )
            except ValueError:
                return False

        if prefix == "HAM":
            try:
                return self._set_attr(
                    main, "hdmi_audio_mode", LegacyHDMIAudioMode(value)
                )
            except ValueError:
                return False

        if prefix == "IPC":
            try:
                return self._set_attr(
                    main, "ip_converter", LegacyIPConverter(value)
                )
            except ValueError:
                return False

        if prefix == "CM2":
            return self._set_attr(main, "component2", value)

        if prefix == "SUR":
            code = value
            if len(code) == 2 and code.startswith("0"):
                code = code[1]
            return self._set_attr(main, "surround_mode", code)

        if prefix == "THX":
            return self._set_attr(main, "thx_mode", value)

        if prefix == "EQM":
            try:
                return self._set_attr(main, "eq_mode", LegacyEQMode(value))
            except ValueError:
                return False

        if prefix == "DHM":
            try:
                return self._set_attr(
                    main, "dolby_headphone_mode", LegacyDolbyHeadphone(value)
                )
            except ValueError:
                return False

        if prefix == "NGT":
            try:
                return self._set_attr(main, "night_mode", LegacyNightMode(value))
            except ValueError:
                return False

        if prefix == "MDA":
            try:
                return self._set_attr(main, "mdax", LegacyMDAX(value))
            except ValueError:
                return False

        if prefix == "LIP":
            try:
                return self._set_attr(main, "lip_sync_ms", int(value))
            except ValueError:
                return False

        if prefix == "SLP":
            try:
                return self._set_attr(main, "sleep_minutes", int(value))
            except ValueError:
                return False

        if prefix == "MNU":
            return self._set_attr(main, "menu_visible", _tristate_to_bool(value))

        if prefix == "OSD":
            return self._set_attr(main, "osd_visible", _tristate_to_bool(value))

        if prefix == "DIP":
            return self._set_attr(main, "display_on", _tristate_to_bool(value))

        if prefix == "FKL":
            return self._set_attr(main, "front_key_lock", _tristate_to_bool(value))

        if prefix == "DCT":
            # Status `DCT:ab` where a=trigger 1, b=trigger 2 (1=OFF, 2=ON).
            changed = False
            if len(value) >= 1:
                changed = self._set_attr(main, "dc_trigger_1", value[0] == "2")
            if len(value) >= 2:
                changed = (
                    self._set_attr(main, "dc_trigger_2", value[1] == "2") or changed
                )
            return changed

        if prefix == "TTO":
            # Status `TTO:1xy` (off) / `TTO:2xy` (on); x=auto/manual, y=channel.
            changed = False
            if len(value) >= 1:
                if value[0] == "1":
                    changed = self._set_attr(main, "test_tone_on", False)
                elif value[0] == "2":
                    changed = self._set_attr(main, "test_tone_on", True)
            if len(value) >= 2:
                changed = (
                    self._set_attr(main, "test_tone_manual", value[1] == "1")
                    or changed
                )
            if len(value) >= 3:
                try:
                    changed = (
                        self._set_attr(main, "test_tone_channel", int(value[2]))
                        or changed
                    )
                except ValueError:
                    pass
            return changed

        if prefix == "TFQ":
            return self._set_attr(main, "tuner_frequency_raw", value)

        if prefix == "TPR":
            try:
                return self._set_attr(main, "tuner_preset", int(value))
            except ValueError:
                return False

        if prefix == "TMD":
            try:
                return self._set_attr(main, "tuner_mode", LegacyTunerMode(value))
            except ValueError:
                return False

        if prefix == "TPI":
            return self._set_attr(
                main, "tuner_preset_info", _tristate_to_bool(value)
            )

        if prefix == "TMC":
            try:
                return self._set_attr(main, "tuner_multicast", int(value))
            except ValueError:
                return False

        if prefix == "CAT":
            # Status `CAT:yxx` where y=1 not searching / 2 searching, xx=00..32.
            changed = False
            if len(value) >= 1:
                changed = self._set_attr(
                    main, "xm_category_searching", value[0] == "2"
                )
            if len(value) >= 3:
                try:
                    changed = (
                        self._set_attr(main, "xm_category_index", int(value[1:]))
                        or changed
                    )
                except ValueError:
                    pass
            return changed

        if prefix == "CHN":
            return self._set_attr(main, "channel_name", value)

        if prefix == "ARN":
            return self._set_attr(main, "artist_name", value)

        if prefix == "SON":
            return self._set_attr(main, "song_title", value)

        if prefix == "CTN":
            return self._set_attr(main, "category_name", value)

        if prefix == "INP":
            try:
                return self._set_attr(main, "input_ad", LegacyInputAD(value))
            except ValueError:
                return False

        if prefix == "ISG":
            try:
                return self._set_attr(main, "input_signal", LegacyInputSignal(value))
            except ValueError:
                return False

        if prefix == "IST":
            try:
                return self._set_attr(main, "input_state", LegacyInputState(value))
            except ValueError:
                return False

        if prefix == "ALS":
            # Auto Lip Sync — answer to `@HAL:?` query.
            return self._set_attr(main, "auto_lip_sync", value == "2")

        if prefix == "SIG":
            try:
                return self._set_attr(
                    main, "signal_format", LegacySignalFormat(value)
                )
            except ValueError:
                return False

        if prefix == "SFQ":
            try:
                return self._set_attr(
                    main, "sampling_frequency", LegacySamplingFrequency(value)
                )
            except ValueError:
                return False

        if prefix == "CHS":
            return self._set_attr(main, "channel_status_raw", value)

        if prefix == "RSV":
            return self._set_attr(main, "firmware_version", value)

        if prefix == "AST":
            return self._set_attr(main, "auto_status_layers", value)

        # Unknown prefixes flow through quietly. Some auto-feedback layers
        # surface prefixes we don't decode yet.
        _LOGGER.debug("Unhandled legacy main prefix: %s = %s", prefix, value)
        return False

    # ----- Multi Room (A or B) ------------------------------------------------

    def _apply_multiroom(
        self, mr: LegacyMultiRoomState, prefix: str, value: str
    ) -> bool:
        if prefix == "MPW":
            return self._set_attr(mr, "power", _tristate_to_bool(value))

        if prefix == "MSP":
            return self._set_attr(mr, "speaker_on", _tristate_to_bool(value))

        if prefix == "MAM":
            return self._set_attr(mr, "mute", _tristate_to_bool(value))

        if prefix == "MSM":
            return self._set_attr(mr, "speaker_mute", _tristate_to_bool(value))

        if prefix == "MVL":
            try:
                return self._set_attr(mr, "line_volume", parse_volume(value))
            except ValueError:
                return False

        if prefix == "MSV":
            try:
                return self._set_attr(mr, "speaker_volume", parse_volume(value))
            except ValueError:
                return False

        if prefix == "MVS":
            try:
                return self._set_attr(
                    mr, "line_volume_mode", LegacyVolumeMode(value)
                )
            except ValueError:
                return False

        if prefix == "MSS":
            try:
                return self._set_attr(
                    mr, "speaker_volume_mode", LegacyVolumeMode(value)
                )
            except ValueError:
                return False

        if prefix == "MSC":
            changed = False
            if len(value) >= 1:
                changed = self._set_attr(mr, "source_video", value[0])
            if len(value) >= 2:
                changed = self._set_attr(mr, "source_audio", value[1]) or changed
            return changed

        if prefix == "MSL":
            try:
                return self._set_attr(mr, "sleep_minutes", int(value))
            except ValueError:
                return False

        if prefix == "MOS":
            return self._set_attr(mr, "osd_visible", _tristate_to_bool(value))

        if prefix == "MST":
            try:
                return self._set_attr(mr, "stereo_mode", LegacyStereoMode(value))
            except ValueError:
                return False

        if prefix == "MTF":
            return self._set_attr(mr, "tuner_frequency_raw", value)

        if prefix == "MTP":
            try:
                return self._set_attr(mr, "tuner_preset", int(value))
            except ValueError:
                return False

        if prefix == "MTM":
            try:
                return self._set_attr(mr, "tuner_mode", LegacyTunerMode(value))
            except ValueError:
                return False

        if prefix == "MMC":
            try:
                return self._set_attr(mr, "tuner_multicast", int(value))
            except ValueError:
                return False

        _LOGGER.debug("Unhandled multi-room prefix: %s = %s", prefix, value)
        return False

    # ----- HD Radio metadata (`*` separator, SR8002) -------------------------

    def _apply_hd_radio(self, prefix: str, value: str) -> bool:
        main = self._state.main
        if prefix == "CHN":
            return self._set_attr(main, "hd_station_name", value)
        if prefix == "ARN":
            return self._set_attr(main, "hd_radio_text", value)
        if prefix == "SON":
            return self._set_attr(main, "hd_program_service", value)
        if prefix == "CTN":
            return self._set_attr(main, "hd_pty_name", value)
        _LOGGER.debug("Unhandled HD Radio prefix: %s = %s", prefix, value)
        return False

    # ----- Convenience -------------------------------------------------------

    def decode_tuner_frequency(self) -> tuple[str, float] | None:
        """Decode the main zone's stored raw tuner frequency, if any."""
        raw = self._state.main.tuner_frequency_raw
        if raw is None:
            return None
        try:
            return decode_tuner_frequency(raw)
        except ValueError:
            return None

    def _notify_subscribers(self) -> None:
        state = self._state.copy() if self._connected else None
        for callback in self._subscribers:
            try:
                callback(state)
            except Exception:
                _LOGGER.exception("Error in state change callback %s", callback)
