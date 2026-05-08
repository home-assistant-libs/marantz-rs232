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
    DigitalInputMode,
    DimmerMode,
    DRC,
    DynamicVolume,
    EcoMode,
    InputSource,
    MULTI_RESPONSE_DELAY,
    MultEQ,
    PROBE_TIMEOUT,
    TunerBand,
    TunerMode,
    _MULTI_RESPONSE_PREFIXES,
    _SINGLE_RESPONSE_PREFIXES,
)
from .players import MainPlayer, ZonePlayer
from .protocol import (
    PendingQuery,
    _ZONE_VOL_RE,
    parse_channel_volume_param,
    parse_volume_param,
)
from .state import MainZoneState, ReceiverState, ZoneState

_LOGGER = logging.getLogger(__name__)


StateCallback = Callable[[ReceiverState | None], None]


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
        )
        self.zone_3 = ZonePlayer(
            self,
            self._state.zone_3,
            power_command="Z3",
            power_standby_parameter="OFF",
            input_source_command="Z3",
            volume_command="Z3",
            mute_command="Z3MU",
        )
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
            prefix = "TF"
            param = message[4:]
            if param not in ("UP", "DOWN", "?"):
                changed = self._set_state_value("tuner_frequency", param)

        elif message.startswith("TPAN"):
            prefix = "TP"
            param = message[4:]
            if param not in ("UP", "DOWN", "?") and not param.startswith("MEM"):
                changed = self._set_state_value("tuner_preset", param)

        elif message.startswith("TMAN"):
            prefix = "TM"
            param = message[4:]
            try:
                changed = self._set_state_value("tuner_band", TunerBand(param))
            except ValueError:
                try:
                    changed = self._set_state_value("tuner_mode", TunerMode(param))
                except ValueError:
                    if param != "?":
                        _LOGGER.warning("Unknown tuner setting: %s", param)

        elif prefix == "Z2":
            if param.startswith("MU"):
                mute_param = param[2:]
                if mute_param == "ON":
                    changed = self._set_attr_value(self._state.zone_2, "mute", True)
                elif mute_param == "OFF":
                    changed = self._set_attr_value(self._state.zone_2, "mute", False)
            else:
                changed = self._process_zone_param(self._state.zone_2, param)

        elif prefix == "Z3":
            if param.startswith("MU"):
                mute_param = param[2:]
                if mute_param == "ON":
                    changed = self._set_attr_value(self._state.zone_3, "mute", True)
                elif mute_param == "OFF":
                    changed = self._set_attr_value(self._state.zone_3, "mute", False)
            else:
                changed = self._process_zone_param(self._state.zone_3, param)

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

        _LOGGER.debug("Unknown PS parameter: %s", param)
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
        if param.startswith("SLP"):
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

    def _notify_subscribers(self) -> None:
        state = self._state.copy() if self._connected else None
        for callback in self._subscribers:
            try:
                callback(state)
            except Exception:
                _LOGGER.exception("Error in state change callback %s", callback)
