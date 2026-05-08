"""Receiver implementation for marantz_rs232."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import serialx

from .const import (
    BAUD_RATE,
    COMMAND_TIMEOUT,
    CR,
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
    MULTI_RESPONSE_DELAY,
    MultEQ,
    PROBE_TIMEOUT,
    TunerBand,
    TunerMode,
    VideoProcessMode,
    ZoneChannelMode,
    _MULTI_RESPONSE_PREFIXES,
    _SINGLE_RESPONSE_PREFIXES,
)
from .players import MainPlayer, Zone4Player, ZonePlayer
from .protocol import (
    PendingQuery,
    _ZONE_VOL_RE,
    parse_channel_volume_param,
    parse_volume_param,
)
from .state import MainZoneState, ReceiverState, Zone4State, ZoneState

_LOGGER = logging.getLogger(__name__)


StateCallback = Callable[[ReceiverState | None], None]


# Zone 2/3 sub-prefixes ordered longest-first so startswith matching is unambiguous.
_ZONE_SUB_PREFIXES = ("STBY", "SLP", "MU", "CS", "CV", "HPF", "PS")


class MarantzReceiver:
    """Async controller for a Marantz receiver over RS232."""

    def __init__(self, port: str) -> None:
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: serialx.SerialStreamWriter | None = None
        self._read_task: asyncio.Task | None = None
        self._state = ReceiverState()
        self.main = MainPlayer(self, self._state.main_zone)
        self.zone_2 = ZonePlayer(
            self,
            self._state.zone_2,
            power_command="Z2",
            power_standby_parameter="OFF",
            input_source_command="Z2",
            volume_command="Z2",
            mute_command="Z2MU",
            sleep_command="Z2SLP",
            auto_standby_command="Z2STBY",
            channel_mode_command="Z2CS",
            channel_volume_command="Z2CV",
            hpf_command="Z2HPF",
            param_command="Z2PS",
        )
        self.zone_3 = ZonePlayer(
            self,
            self._state.zone_3,
            power_command="Z3",
            power_standby_parameter="OFF",
            input_source_command="Z3",
            volume_command="Z3",
            mute_command="Z3MU",
            sleep_command="Z3SLP",
            auto_standby_command="Z3STBY",
            channel_mode_command="Z3CS",
            channel_volume_command="Z3CV",
            hpf_command="Z3HPF",
            param_command="Z3PS",
        )
        self.zone_4 = Zone4Player(self, self._state.zone_4)
        self._subscribers: list[StateCallback] = []
        self._pending_queries: list[PendingQuery] = []
        self._write_lock = asyncio.Lock()
        self._connected = False

    @property
    def state(self) -> ReceiverState:
        return self._state.copy()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def power(self) -> bool | None:
        return self._state.power

    def subscribe(self, callback: StateCallback) -> Callable[[], None]:
        self._subscribers.append(callback)
        return lambda: self._subscribers.remove(callback)

    async def connect(self) -> None:
        self._reader, self._writer = await serialx.open_serial_connection(
            self._port,
            baudrate=BAUD_RATE,
        )
        self._connected = True
        self._read_task = asyncio.create_task(self._read_loop())

        try:
            await self.query_power()
        except TimeoutError:
            await self.disconnect()
            raise ConnectionError(
                f"No response from receiver on {self._port}"
            ) from None

        _LOGGER.info("Connected to Marantz receiver on %s", self._port)

    async def disconnect(self) -> None:
        await self._teardown()
        _LOGGER.info("Disconnected from Marantz receiver")

    async def power_on(self) -> None:
        await self._send_command("PW", "ON")

    async def power_standby(self) -> None:
        await self._send_command("PW", "STANDBY")

    async def query_power(self) -> bool:
        resp = await self._query("PW")
        if resp == "ON":
            return True
        if resp == "STANDBY":
            return False
        raise ValueError(f"Unknown power state: {resp}")

    async def query_state(self) -> None:
        for prefix in _SINGLE_RESPONSE_PREFIXES:
            if prefix == "PW":
                continue
            try:
                await self._query(prefix)
            except TimeoutError:
                pass

        for prefix in _MULTI_RESPONSE_PREFIXES:
            await self._send_command(prefix, "?")
            await asyncio.sleep(MULTI_RESPONSE_DELAY)

    async def probe_sources(
        self, timeout: float | None = None
    ) -> frozenset[InputSource]:
        if not self._connected:
            raise ConnectionError("Not connected")

        if timeout is None:
            timeout = PROBE_TIMEOUT

        original = self._state.main_zone.input_source
        available: set[InputSource] = set()

        if original is not None:
            available.add(original)

        for source in InputSource:
            if source == original:
                continue
            resp = await self._send_and_wait("SI", source.value, timeout=timeout)
            if resp == source.value:
                available.add(source)

        if original is not None:
            await self._send_and_wait("SI", original.value)

        return frozenset(available)

    async def _send_and_wait(
        self, prefix: str, param: str, timeout: float | None = None
    ) -> str | None:
        if timeout is None:
            timeout = PROBE_TIMEOUT

        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        pending = PendingQuery(prefix=prefix, future=future)
        self._pending_queries.append(pending)
        try:
            await self._send_command(prefix, param)
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            return None
        finally:
            if pending in self._pending_queries:
                self._pending_queries.remove(pending)

    async def _send_command(self, command: str, parameter: str) -> None:
        assert self._writer is not None
        msg = f"{command}{parameter}\r".encode("ascii")
        _LOGGER.debug("Sending: %s", msg)
        try:
            async with self._write_lock:
                self._writer.write(msg)
                await self._writer.drain()
        except Exception:
            _LOGGER.exception("Error writing to serial port")
            await self._teardown()
            raise

    async def _query(self, command: str) -> str:
        assert self._writer is not None
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        pending = PendingQuery(prefix=command, future=future)
        self._pending_queries.append(pending)

        try:
            msg = f"{command}?\r".encode("ascii")
            _LOGGER.debug("Querying: %s", msg)
            try:
                async with self._write_lock:
                    self._writer.write(msg)
                    await self._writer.drain()
            except Exception:
                _LOGGER.exception("Error writing to serial port")
                await self._teardown()
                raise
            return await asyncio.wait_for(future, timeout=COMMAND_TIMEOUT)
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

            while CR in buf:
                line, buf = buf.split(CR, 1)
                if not line:
                    continue
                message = line.decode("ascii", errors="replace").strip()
                if message:
                    self._process_message(message)

    @staticmethod
    def _set_attr_value(target: object, attr: str, new_value: object) -> bool:
        if getattr(target, attr) == new_value:
            return False
        setattr(target, attr, new_value)
        return True

    def _set_state_value(self, attr: str, new_value: object) -> bool:
        return self._set_attr_value(self._state.main_zone, attr, new_value)

    def _process_message(self, message: str) -> None:
        _LOGGER.debug("Received: %s", message)

        if len(message) < 2:
            return

        prefix = message[:2]
        param = message[2:]

        if prefix == "MV" and param.startswith("MAX"):
            prefix = "MVMAX"
            param = param.removeprefix("MAX").strip()
        elif prefix == "MV" and param.startswith("MIN"):
            prefix = "MVMIN"
            param = param.removeprefix("MIN").strip()

        changed = False

        if prefix == "PW":
            if param == "ON":
                changed = self._set_attr_value(self._state, "power", True)
            elif param == "STANDBY":
                changed = self._set_attr_value(self._state, "power", False)
            else:
                _LOGGER.warning("Unknown power state: %s", param)

        elif prefix == "ZM":
            changed = self._set_state_value("power", param == "ON")

        elif prefix == "MV":
            try:
                changed = self._set_state_value("volume", parse_volume_param(param))
            except (ValueError, IndexError):
                _LOGGER.warning("Could not parse volume: %s", param)

        elif prefix == "MVMAX":
            try:
                changed = self._set_state_value("volume_max", parse_volume_param(param))
            except (ValueError, IndexError):
                _LOGGER.warning("Could not parse max volume: %s", param)

        elif prefix == "MVMIN":
            try:
                changed = self._set_state_value("volume_min", parse_volume_param(param))
            except (ValueError, IndexError):
                _LOGGER.warning("Could not parse min volume: %s", param)

        elif prefix == "MU":
            changed = self._set_state_value("mute", param == "ON")

        elif prefix == "SI":
            try:
                changed = self._set_state_value("input_source", InputSource(param))
            except ValueError:
                _LOGGER.warning("Unknown input source: %s", param)

        elif prefix == "MS":
            if param.startswith("SMART") or param.startswith("FAVORITE"):
                # Smart Select / Favorite acknowledgements aren't tracked in state.
                pass
            else:
                changed = self._set_state_value("surround_mode", param)

        elif prefix == "CV":
            channel, sep, val = param.partition(" ")
            if sep and val not in ("UP", "DOWN"):
                try:
                    new_value = parse_channel_volume_param(val)
                    if self._state.main_zone.channel_volumes.get(channel) != new_value:
                        self._state.main_zone.channel_volumes[channel] = new_value
                        changed = True
                except (ValueError, IndexError):
                    _LOGGER.warning("Could not parse channel volume: %s", param)

        elif prefix == "PS":
            changed = self._process_ps_param(param)

        elif prefix == "SD":
            if param == "NO":
                changed = self._set_state_value("digital_input", None)
            else:
                try:
                    changed = self._set_state_value(
                        "digital_input",
                        DigitalInputMode(param),
                    )
                except ValueError:
                    _LOGGER.warning("Unknown digital input mode: %s", param)

        elif prefix == "DC":
            try:
                changed = self._set_state_value(
                    "audio_decode",
                    AudioDecodeMode(param),
                )
            except ValueError:
                _LOGGER.warning("Unknown audio decode mode: %s", param)

        elif prefix == "SV":
            if param in ("SOURCE", "OFF"):
                changed = self._set_state_value("video_select", None)
            elif param in ("ON",):
                pass
            else:
                try:
                    changed = self._set_state_value("video_select", InputSource(param))
                except ValueError:
                    _LOGGER.warning("Unknown video source: %s", param)

        elif prefix == "VS":
            prefix, param, changed = self._process_vs_message(message)

        elif prefix == "PV":
            # Picture mode/video adjustments — not tracked in state, swallow.
            pass

        elif prefix == "MN":
            # Cursor / menu command echoes — not tracked in state.
            pass

        elif prefix == "TR":
            prefix, param, changed = self._process_tr_message(message)

        elif prefix == "SY":
            prefix, param, changed = self._process_sy_message(message)

        elif prefix == "SS":
            # System settings echoes — not tracked in state for now.
            pass

        elif message.startswith("SLP"):
            prefix = "SLP"
            param = message[3:]
            if param == "OFF":
                changed = self._set_state_value("sleep", None)
            elif param != "?":
                changed = self._set_state_value("sleep", param)

        elif message.startswith("ECO"):
            prefix = "ECO"
            param = message[3:]
            try:
                changed = self._set_state_value("eco", EcoMode(param))
            except ValueError:
                if param != "?":
                    _LOGGER.warning("Unknown ECO mode: %s", param)

        elif message.startswith("STBY"):
            prefix = "STBY"
            param = message[4:]
            if param == "OFF":
                changed = self._set_state_value("auto_standby", None)
            elif param != "?":
                changed = self._set_state_value("auto_standby", param)

        elif message.startswith("DIM"):
            prefix = "DIM"
            param = message[3:].strip()
            try:
                changed = self._set_state_value("dimmer", DimmerMode(param))
            except ValueError:
                if param not in ("?", "SEL"):
                    _LOGGER.warning("Unknown dimmer mode: %s", param)

        elif message.startswith("TFAN"):
            prefix = "TFAN"
            param = message[4:]
            if param not in ("UP", "DOWN", "?"):
                changed = self._set_state_value("tuner_frequency", param)

        elif message.startswith("TPAN"):
            prefix = "TPAN"
            param = message[4:]
            if param not in ("UP", "DOWN", "?") and not param.startswith("MEM"):
                changed = self._set_state_value("tuner_preset", param)

        elif message.startswith("TMAN"):
            prefix = "TMAN"
            param = message[4:]
            try:
                changed = self._set_state_value("tuner_band", TunerBand(param))
            except ValueError:
                try:
                    changed = self._set_state_value("tuner_mode", TunerMode(param))
                except ValueError:
                    if param != "?":
                        _LOGGER.warning("Unknown tuner setting: %s", param)

        elif message.startswith("Z2"):
            prefix, param, changed = self._process_zone_message(
                self._state.zone_2, "Z2", message
            )

        elif message.startswith("Z3"):
            prefix, param, changed = self._process_zone_message(
                self._state.zone_3, "Z3", message
            )

        elif message.startswith("Z4"):
            prefix, param, changed = self._process_zone4_message(message)

        for pending in list(self._pending_queries):
            if pending.prefix == prefix and not pending.future.done():
                pending.future.set_result(param)

        if changed:
            self._notify_subscribers()

    def _process_ps_param(self, param: str) -> bool:
        if param.startswith("TONE CTRL "):
            val = param[10:]
            if val == "ON":
                return self._set_state_value("tone_control", True)
            if val == "OFF":
                return self._set_state_value("tone_control", False)
            return False

        if param.startswith("BAS "):
            val = param[4:]
            if val in ("UP", "DOWN", "?"):
                return False
            try:
                return self._set_state_value("bass", int(val) - 50)
            except ValueError:
                return False

        if param.startswith("TRE "):
            val = param[4:]
            if val in ("UP", "DOWN", "?"):
                return False
            try:
                return self._set_state_value("treble", int(val) - 50)
            except ValueError:
                return False

        if param == "CINEMA EQ.ON":
            return self._set_state_value("cinema_eq", True)
        if param == "CINEMA EQ.OFF":
            return self._set_state_value("cinema_eq", False)

        if param.startswith("MULTEQ:"):
            val = param[7:]
            if val == "?":
                return False
            try:
                return self._set_state_value("multeq", MultEQ(val))
            except ValueError:
                _LOGGER.warning("Unknown MultEQ mode: %s", val)
                return False

        if param.startswith("DYNEQ "):
            val = param[6:]
            if val == "ON":
                return self._set_state_value("dynamic_eq", True)
            if val == "OFF":
                return self._set_state_value("dynamic_eq", False)
            return False

        if param.startswith("DYNVOL "):
            val = param[7:]
            if val == "?":
                return False
            try:
                return self._set_state_value("dynamic_volume", DynamicVolume(val))
            except ValueError:
                _LOGGER.warning("Unknown dynamic volume: %s", val)
                return False

        if param.startswith("DRC "):
            val = param[4:]
            if val == "?":
                return False
            try:
                return self._set_state_value("drc", DRC(val))
            except ValueError:
                _LOGGER.warning("Unknown DRC mode: %s", val)
                return False

        if param.startswith("SWR "):
            val = param[4:]
            if val == "ON":
                return self._set_state_value("subwoofer", True)
            if val == "OFF":
                return self._set_state_value("subwoofer", False)
            return False

        if param.startswith("LOM "):
            val = param[4:]
            if val == "ON":
                return self._set_state_value("loudness", True)
            if val == "OFF":
                return self._set_state_value("loudness", False)
            return False

        if param.startswith("DEH "):
            val = param[4:]
            if val == "?":
                return False
            try:
                return self._set_state_value("dialog_enhancer", DialogEnhancer(val))
            except ValueError:
                _LOGGER.warning("Unknown dialog enhancer mode: %s", val)
                return False

        if param.startswith("HTEQ "):
            val = param[5:]
            if val == "ON":
                return self._set_state_value("ht_eq", True)
            if val == "OFF":
                return self._set_state_value("ht_eq", False)
            return False

        if param.startswith("LFC "):
            val = param[4:]
            if val == "ON":
                return self._set_state_value("audyssey_lfc", True)
            if val == "OFF":
                return self._set_state_value("audyssey_lfc", False)
            return False

        if param.startswith("MDAX "):
            val = param[5:]
            if val == "?":
                return False
            try:
                return self._set_state_value("mdax", MDAX(val))
            except ValueError:
                _LOGGER.warning("Unknown M-DAX mode: %s", val)
                return False

        if param.startswith("DELAY "):
            val = param[6:]
            if val in ("UP", "DOWN", "?"):
                return False
            try:
                return self._set_state_value("audio_delay", int(val))
            except ValueError:
                return False

        if param.startswith("NEURAL "):
            val = param[7:]
            if val == "ON":
                return self._set_state_value("neural_x", True)
            if val == "OFF":
                return self._set_state_value("neural_x", False)
            return False

        if param.startswith("DCO "):
            val = param[4:]
            if val == "?":
                return False
            try:
                return self._set_state_value("d_comp", DComp(val))
            except ValueError:
                _LOGGER.warning("Unknown D.COMP mode: %s", val)
                return False

        if param.startswith("BSC "):
            val = param[4:]
            if val in ("UP", "DOWN", "?"):
                return False
            try:
                return self._set_state_value("bass_sync", int(val))
            except ValueError:
                return False

        if param.startswith("LFE "):
            val = param[4:]
            if val in ("UP", "DOWN", "?"):
                return False
            try:
                return self._set_state_value("lfe", -abs(int(val)))
            except ValueError:
                return False

        if param.startswith("REFLEV "):
            val = param[7:]
            if val == "?":
                return False
            try:
                return self._set_state_value("reference_level", int(val))
            except ValueError:
                return False

        if param.startswith("GEQ "):
            val = param[4:]
            if val == "ON":
                return self._set_state_value("graphic_eq", True)
            if val == "OFF":
                return self._set_state_value("graphic_eq", False)
            return False

        if param.startswith("HEQ "):
            val = param[4:]
            if val == "ON":
                return self._set_state_value("headphone_eq", True)
            if val == "OFF":
                return self._set_state_value("headphone_eq", False)
            return False

        _LOGGER.debug("Unknown PS parameter: %s", param)
        return False

    def _process_vs_message(self, message: str) -> tuple[str, str, bool]:
        """Parse VS* responses (HDMI/video)."""
        param = message[2:]
        changed = False

        if param.startswith("MONI"):
            try:
                changed = self._set_state_value("hdmi_monitor", HDMIMonitor(param))
            except ValueError:
                if param != "MONI ?":
                    _LOGGER.debug("Unknown HDMI monitor: %s", param)
        elif param.startswith("AUDIO"):
            if param == "AUDIO ?":
                pass
            else:
                try:
                    changed = self._set_state_value(
                        "hdmi_audio_output", HDMIAudioOutput(param)
                    )
                except ValueError:
                    _LOGGER.debug("Unknown HDMI audio output: %s", param)
        elif param.startswith("SC"):
            try:
                changed = self._set_state_value("hdmi_resolution", HDMIResolution(param))
            except ValueError:
                if not param.endswith("?"):
                    _LOGGER.debug("Unknown HDMI resolution: %s", param)
        elif param.startswith("VPM"):
            try:
                changed = self._set_state_value(
                    "video_process_mode", VideoProcessMode(param)
                )
            except ValueError:
                if param != "VPM ?":
                    _LOGGER.debug("Unknown video process mode: %s", param)
        else:
            _LOGGER.debug("Unhandled VS message: %s", message)

        return "VS", param, changed

    def _process_tr_message(self, message: str) -> tuple[str, str, bool]:
        """Parse TR1/TR2 trigger responses."""
        param = message[2:]
        changed = False

        if param == "1 ON":
            changed = self._set_state_value("trigger_1", True)
        elif param == "1 OFF":
            changed = self._set_state_value("trigger_1", False)
        elif param == "2 ON":
            changed = self._set_state_value("trigger_2", True)
        elif param == "2 OFF":
            changed = self._set_state_value("trigger_2", False)

        return "TR", param, changed

    def _process_sy_message(self, message: str) -> tuple[str, str, bool]:
        """Parse SY* lock responses."""
        param = message[2:]
        changed = False

        if param == "REMOTE LOCK ON":
            changed = self._set_state_value("remote_lock", True)
        elif param == "REMOTE LOCK OFF":
            changed = self._set_state_value("remote_lock", False)
        elif param in ("PANEL LOCK ON", "PANEL+V LOCK ON"):
            changed = self._set_state_value("panel_lock", True)
        elif param == "PANEL LOCK OFF":
            changed = self._set_state_value("panel_lock", False)

        return "SY", param, changed

    def _process_zone_message(
        self, zone: ZoneState, zone_prefix: str, message: str
    ) -> tuple[str, str, bool]:
        """Parse Z2*/Z3* responses, returning (matched_prefix, param, changed)."""
        rest = message[2:]

        # Sub-prefix matches first (longest-first).
        for sub in _ZONE_SUB_PREFIXES:
            if rest.startswith(sub):
                sub_param = rest[len(sub):]
                full_prefix = f"{zone_prefix}{sub}"
                changed = self._process_zone_sub(zone, sub, sub_param)
                return full_prefix, sub_param, changed

        # Otherwise: power, source, volume, smart/favorite, source-cancel.
        changed = self._process_zone_param(zone, rest)
        return zone_prefix, rest, changed

    def _process_zone_sub(
        self, zone: ZoneState, sub: str, param: str
    ) -> bool:
        """Handle Z*<sub><param> messages."""
        if sub == "MU":
            if param == "ON":
                return self._set_attr_value(zone, "mute", True)
            if param == "OFF":
                return self._set_attr_value(zone, "mute", False)
            return False

        if sub == "STBY":
            if param == "OFF":
                return self._set_attr_value(zone, "auto_standby", None)
            if param != "?":
                return self._set_attr_value(zone, "auto_standby", param)
            return False

        if sub == "SLP":
            if param == "OFF":
                return self._set_attr_value(zone, "sleep", None)
            if param != "?":
                return self._set_attr_value(zone, "sleep", param)
            return False

        if sub == "CS":
            try:
                return self._set_attr_value(zone, "channel_mode", ZoneChannelMode(param))
            except ValueError:
                if param != "?":
                    _LOGGER.warning("Unknown zone channel mode: %s", param)
                return False

        if sub == "HPF":
            if param == "ON":
                return self._set_attr_value(zone, "hpf", True)
            if param == "OFF":
                return self._set_attr_value(zone, "hpf", False)
            return False

        if sub == "CV":
            channel, sep, val = param.partition(" ")
            if sep and val not in ("UP", "DOWN"):
                try:
                    new_value = parse_channel_volume_param(val)
                    if zone.channel_volumes.get(channel) != new_value:
                        zone.channel_volumes[channel] = new_value
                        return True
                except (ValueError, IndexError):
                    _LOGGER.warning("Could not parse zone channel volume: %s", param)
            return False

        if sub == "PS":
            if param.startswith("BAS "):
                val = param[4:]
                if val in ("UP", "DOWN", "?"):
                    return False
                try:
                    return self._set_attr_value(zone, "bass", int(val) - 50)
                except ValueError:
                    return False
            if param.startswith("TRE "):
                val = param[4:]
                if val in ("UP", "DOWN", "?"):
                    return False
                try:
                    return self._set_attr_value(zone, "treble", int(val) - 50)
                except ValueError:
                    return False
            return False

        return False

    def _process_zone_param(self, zone: ZoneState, param: str) -> bool:
        if param == "ON":
            return self._set_attr_value(zone, "power", True)
        if param == "OFF":
            return self._set_attr_value(zone, "power", False)
        if param in ("UP", "DOWN"):
            return False
        if _ZONE_VOL_RE.match(param):
            try:
                return self._set_attr_value(zone, "volume", parse_volume_param(param))
            except (ValueError, IndexError):
                return False
        if param.startswith("SMART"):
            return False
        if param.startswith("FAVORITE"):
            return False
        if param == "SOURCE":
            return self._set_attr_value(zone, "input_source", None)
        try:
            return self._set_attr_value(zone, "input_source", InputSource(param))
        except ValueError:
            _LOGGER.warning("Unknown zone source: %s", param)
            return False

    def _process_zone4_message(self, message: str) -> tuple[str, str, bool]:
        """Parse Z4* responses."""
        rest = message[2:]
        zone = self._state.zone_4

        if rest.startswith("SLP"):
            param = rest[3:]
            changed = False
            if param == "OFF":
                changed = self._set_attr_value(zone, "sleep", None)
            elif param != "?":
                changed = self._set_attr_value(zone, "sleep", param)
            return "Z4SLP", param, changed

        if rest == "ON":
            return "Z4", rest, self._set_attr_value(zone, "power", True)
        if rest == "OFF":
            return "Z4", rest, self._set_attr_value(zone, "power", False)
        if rest == "SOURCE":
            return "Z4", rest, self._set_attr_value(zone, "input_source", None)

        # Try input source
        try:
            changed = self._set_attr_value(zone, "input_source", InputSource(rest))
            return "Z4", rest, changed
        except ValueError:
            _LOGGER.debug("Unknown Z4 message: %s", message)
            return "Z4", rest, False

    def _notify_subscribers(self) -> None:
        state = self._state.copy() if self._connected else None
        for callback in self._subscribers:
            try:
                callback(state)
            except Exception:
                _LOGGER.exception("Error in state change callback %s", callback)
