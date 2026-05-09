"""Receiver implementation for the v2003 (SR9300/SR8300) Marantz protocol.

The wire is half-duplex: the host sends a command or query and must wait for
the response before sending the next request. We enforce that with a single
asyncio.Lock around every send.

Responses come in two shapes:

* ACK / NAK — a bare ``0x06`` or ``0x15`` byte after a *command*.
* Status answer — an ``@<ID>...\\r`` line after a *query*.

The read loop processes incoming bytes one at a time and routes them to
whichever future is currently waiting.
"""

from __future__ import annotations

import asyncio
import copy
import logging
from collections.abc import Callable

import serialx

from .const import (
    ACK_BYTE,
    DEFAULT_DEVICE_ID,
    NAK_BYTE,
    POWER_STATUS_CODES,
    SURROUND_STATUS_CODES,
    V2003_BAUD_RATE,
    V2003_COMMAND_TIMEOUT,
    V2003_TERMINATOR,
    V2003DisplayMode,
    V2003InputMode,
    V2003MultiRoomVolumeMode,
    V2003Power,
    V2003SamplingFrequency,
    V2003SignalFormat,
    V2003Source,
    V2003TestTone,
    V2003TestToneMode,
    V2003TunerBand,
    V2003TunerMode,
)
from .players import V2003MainPlayer, V2003MultiRoomPlayer
from .protocol import (
    decode_audio_source,
    decode_multi_audio_source,
    decode_multi_tuner_preset,
    decode_multi_video_source,
    decode_tuner_frequency,
    decode_tuner_preset,
    decode_video_source,
    encode_command,
    encode_query,
    is_main_multi_channel_input,
    parse_line,
    parse_multi_sleep,
    parse_multi_volume,
    parse_sleep,
    parse_tone,
    parse_volume,
)
from .state import V2003MainState, V2003MultiRoomState, V2003ReceiverState

_LOGGER = logging.getLogger(__name__)


V2003StateCallback = Callable[[V2003ReceiverState | None], None]


# Single-letter status request characters we issue from `query_state()`.
# Order matters only for human readability of the resulting log.
_MAIN_QUERY_CHARS = (
    "A",  # power
    "B",  # video input
    "C",  # audio input
    "D",  # input mode
    "E",  # tuner frequency
    "F",  # tuner preset
    "G",  # tuner mode
    "H",  # volume
    "I",  # bass
    "J",  # treble
    "K",  # ATT
    "L",  # surround mode
    "M",  # sleep
    "N",  # display
    "O",  # OSD
    "P",  # test tone channel
    "Q",  # test tone mode
    "R",  # night mode
    "S",  # menu
    "T",  # F-direct
    "U",  # signal format
    "V",  # sampling frequency
    "W",  # channel status (raw hex)
)

_MULTI_QUERY_CHARS = (
    "X",  # multi-room enabled
    "Y",  # MR video input
    "Z",  # MR audio input
    "a",  # MR tuner frequency
    "b",  # MR tuner preset
    "c",  # MR volume
    "d",  # MR volume mode
    "e",  # MR sleep
    "f",  # MR OSD
    "g",  # MR speaker
    "h",  # MR mute
)


class MarantzV2003Receiver:
    """Async controller for SR9300/SR8300-era Marantz AV receivers.

    The receiver requires 4800 8N1 with RTS/CTS hardware flow control. The
    serial cable must be a *straight* (not null-modem) DB9 connection.
    """

    def __init__(
        self,
        port: str,
        *,
        device_id: str = DEFAULT_DEVICE_ID,
    ) -> None:
        if not (len(device_id) == 1 and device_id in "0123456789"):
            raise ValueError(f"device_id must be a single digit '0'..'9', got {device_id!r}")
        self._port = port
        self._device_id = device_id
        self._reader: asyncio.StreamReader | None = None
        self._writer: serialx.SerialStreamWriter | None = None  # type: ignore[type-arg]
        self._read_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()
        self._pending_ack: asyncio.Future[bool] | None = None
        self._pending_query_char: str | None = None
        self._pending_query_future: asyncio.Future[str] | None = None
        self._state = V2003ReceiverState(device_id=device_id)
        self._subscribers: list[V2003StateCallback] = []
        self._connected = False

        self.main = V2003MainPlayer(self)
        self.multi_room = V2003MultiRoomPlayer(self)

    # -- Connection lifecycle --

    async def connect(self) -> None:
        if self._connected:
            return
        self._reader, self._writer = await serialx.open_serial_connection(
            self._port,
            baudrate=V2003_BAUD_RATE,
            rtscts=True,
        )
        self._read_task = asyncio.create_task(self._read_loop())
        # Verify the link by querying power. If the receiver doesn't answer
        # within COMMAND_TIMEOUT we treat it as a connection failure.
        try:
            await self._query("A")
        except (asyncio.TimeoutError, ConnectionError) as err:
            await self.disconnect()
            raise ConnectionError(
                f"No response from v2003 receiver on {self._port}: {err}"
            ) from err
        self._connected = True

    async def disconnect(self) -> None:
        if self._read_task is not None:
            self._read_task.cancel()
            try:
                await self._read_task
            except (asyncio.CancelledError, Exception):
                pass
            self._read_task = None
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # pragma: no cover - best-effort teardown
                pass
            self._writer = None
        self._reader = None
        self._connected = False
        self._notify(None)

    # -- Public API --

    @property
    def state(self) -> V2003ReceiverState:
        return copy.deepcopy(self._state)

    def subscribe(self, callback: V2003StateCallback) -> Callable[[], None]:
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    async def query_state(self) -> None:
        """Poll all status requests once."""
        for ch in _MAIN_QUERY_CHARS + _MULTI_QUERY_CHARS:
            try:
                await self._query(ch)
            except (asyncio.TimeoutError, ValueError) as err:
                _LOGGER.debug("Query '?%s' failed: %s", ch, err)

    # -- Internal: send / query --

    async def _send_command(self, code: str) -> None:
        """Send a normal command and await the ACK byte."""
        if self._writer is None:
            raise ConnectionError("Receiver is not connected")
        loop = asyncio.get_running_loop()
        async with self._send_lock:
            self._pending_ack = loop.create_future()
            self._writer.write(encode_command(self._device_id, code))
            await self._writer.drain()
            try:
                ok = await asyncio.wait_for(
                    self._pending_ack, timeout=V2003_COMMAND_TIMEOUT
                )
            finally:
                self._pending_ack = None
        if not ok:
            raise ValueError(f"Receiver NAK'd command {code!r}")

    async def _query(self, request_char: str) -> str:
        """Send a status request and return the answer payload (without the
        leading ``@<ID>``)."""
        if self._writer is None:
            raise ConnectionError("Receiver is not connected")
        loop = asyncio.get_running_loop()
        async with self._send_lock:
            self._pending_query_char = request_char
            self._pending_query_future = loop.create_future()
            self._writer.write(encode_query(self._device_id, request_char))
            await self._writer.drain()
            try:
                payload = await asyncio.wait_for(
                    self._pending_query_future, timeout=V2003_COMMAND_TIMEOUT
                )
            finally:
                self._pending_query_char = None
                self._pending_query_future = None
        return payload

    # -- Read loop --

    async def _read_loop(self) -> None:
        assert self._reader is not None
        try:
            while True:
                byte = await self._reader.read(1)
                if not byte:
                    break  # EOF — port closed
                if byte == ACK_BYTE:
                    self._resolve_ack(True)
                elif byte == NAK_BYTE:
                    self._resolve_ack(False)
                elif byte == b"@":
                    rest = await self._reader.readuntil(V2003_TERMINATOR)
                    line = (byte + rest).decode("ascii", errors="replace").rstrip()
                    self._dispatch(line)
                else:
                    _LOGGER.debug("Discarding unexpected byte: %r", byte)
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            _LOGGER.exception("v2003 read loop crashed")

    def _resolve_ack(self, ok: bool) -> None:
        fut = self._pending_ack
        if fut is not None and not fut.done():
            fut.set_result(ok)

    def _dispatch(self, line: str) -> None:
        parsed = parse_line(line, expected_id=self._device_id)
        if parsed is None:
            _LOGGER.debug("Ignoring line for wrong/missing ID: %r", line)
            return
        _, payload = parsed
        # Resolve a pending query if its request character matches.
        char = self._pending_query_char
        fut = self._pending_query_future
        if char is not None and fut is not None and not fut.done():
            if payload.startswith(char):
                fut.set_result(payload)
        # Route into state regardless — even if no one was waiting, we still
        # want the state object updated.
        try:
            changed = self._update_state(payload)
        except Exception:  # pragma: no cover
            _LOGGER.exception("Failed to update state for %r", payload)
            changed = False
        if changed:
            self._notify(self._state)

    # -- State updates --

    def _update_state(self, payload: str) -> bool:
        """Apply a status-answer payload to ``self._state``. Returns True if
        anything in state actually changed.
        """
        # The first character indicates which field this answer is for.
        head = payload[:1]
        m = self._state.main
        mr = self._state.multi_room

        # Power: A0 = ON, A1 = OFF.
        if head == "A":
            new_power = POWER_STATUS_CODES.get(payload)
            if new_power is None:
                return False
            return _set_attr(m, "power", new_power)

        if head == "B":
            return _set_attr(m, "video_input", decode_video_source(payload))

        if head == "C":
            mci = is_main_multi_channel_input(payload)
            changed = _set_attr(m, "multi_channel_input", mci)
            if mci:
                # MCI mode — audio_input is not a discrete source.
                changed |= _set_attr(m, "audio_input", None)
                return changed
            src = decode_audio_source(payload)
            changed |= _set_attr(m, "audio_input", src)
            # Inferring tuner band from audio input.
            band = {
                V2003Source.FM: V2003TunerBand.FM,
                V2003Source.AM: V2003TunerBand.AM,
                V2003Source.MW: V2003TunerBand.MW,
                V2003Source.LW: V2003TunerBand.LW,
            }.get(src) if src else None
            if band is not None:
                changed |= _set_attr(m, "tuner_band", band)
            return changed

        if head == "D":
            try:
                return _set_attr(m, "input_mode", V2003InputMode(payload))
            except ValueError:
                return False

        if head == "E":
            if payload == "E-":
                return _set_attr(m, "tuner_frequency", None) | _set_attr(
                    m, "tuner_frequency_raw", None
                )
            try:
                decoded = decode_tuner_frequency(payload, m.tuner_band)
            except ValueError:
                return False
            if decoded is None:
                return False
            band, freq = decoded
            return (
                _set_attr(m, "tuner_band", band)
                | _set_attr(m, "tuner_frequency", freq)
                | _set_attr(m, "tuner_frequency_raw", payload[2:])
            )

        if head == "F":
            try:
                preset = decode_tuner_preset(payload)
            except ValueError:
                return False
            return _set_attr(m, "tuner_preset", preset)

        if head == "G":
            try:
                return _set_attr(m, "tuner_mode", V2003TunerMode(payload))
            except ValueError:
                return False

        if head == "H":
            try:
                vol, muted = parse_volume(payload)
            except ValueError:
                return False
            return _set_attr(m, "volume", vol) | _set_attr(m, "mute", muted)

        if head == "I":
            try:
                return _set_attr(m, "bass", parse_tone(payload))
            except ValueError:
                return False

        if head == "J":
            try:
                return _set_attr(m, "treble", parse_tone(payload))
            except ValueError:
                return False

        if head == "K":
            return _set_attr(m, "attenuator", payload == "K1")

        if head == "L":
            mode = SURROUND_STATUS_CODES.get(payload)
            if mode is None:
                return False
            return _set_attr(m, "surround_mode", mode)

        if head == "M":
            try:
                return _set_attr(m, "sleep_minutes", parse_sleep(payload))
            except ValueError:
                return False

        if head == "N":
            try:
                return _set_attr(m, "display", V2003DisplayMode(payload))
            except ValueError:
                return False

        if head == "O":
            return _set_attr(m, "osd", payload == "O0")

        if head == "P":
            try:
                return _set_attr(m, "test_tone", V2003TestTone(payload))
            except ValueError:
                return False

        if head == "Q":
            try:
                return _set_attr(m, "test_tone_mode", V2003TestToneMode(payload))
            except ValueError:
                return False

        if head == "R":
            return _set_attr(m, "night_mode", payload == "R0")

        if head == "S":
            return _set_attr(m, "menu_visible", payload == "S0")

        if head == "T":
            if payload == "T-":
                return _set_attr(m, "f_direct", None)
            return _set_attr(m, "f_direct", payload == "T1")

        if head == "U":
            try:
                return _set_attr(m, "signal_format", V2003SignalFormat(payload[1:]))
            except (ValueError, IndexError):
                return False

        if head == "V":
            try:
                return _set_attr(
                    m, "sampling_frequency", V2003SamplingFrequency(payload[1:])
                )
            except (ValueError, IndexError):
                return False

        if head == "W":
            if payload == "W-":
                return _set_attr(m, "channel_status_raw", None)
            return _set_attr(m, "channel_status_raw", payload[1:])

        # Multi-room responses
        if head == "X":
            return _set_attr(mr, "enabled", payload == "X0")

        if head == "Y":
            return _set_attr(mr, "video_input", decode_multi_video_source(payload))

        if head == "Z":
            src = decode_multi_audio_source(payload)
            changed = _set_attr(mr, "audio_input", src)
            band = {
                V2003Source.FM: V2003TunerBand.FM,
                V2003Source.AM: V2003TunerBand.AM,
                V2003Source.MW: V2003TunerBand.MW,
                V2003Source.LW: V2003TunerBand.LW,
            }.get(src) if src else None
            if band is not None:
                changed |= _set_attr(mr, "tuner_band", band)
            return changed

        if head == "a":
            if payload == "a-":
                return _set_attr(mr, "tuner_frequency", None) | _set_attr(
                    mr, "tuner_frequency_raw", None
                )
            try:
                decoded = decode_tuner_frequency(payload, mr.tuner_band)
            except ValueError:
                return False
            if decoded is None:
                return False
            band, freq = decoded
            return (
                _set_attr(mr, "tuner_band", band)
                | _set_attr(mr, "tuner_frequency", freq)
                | _set_attr(mr, "tuner_frequency_raw", payload[2:])
            )

        if head == "b":
            try:
                return _set_attr(mr, "tuner_preset", decode_multi_tuner_preset(payload))
            except ValueError:
                return False

        if head == "c":
            try:
                vol, muted = parse_multi_volume(payload)
            except ValueError:
                return False
            changed = _set_attr(mr, "volume", vol)
            if muted:
                changed |= _set_attr(mr, "mute", True)
            return changed

        if head == "d":
            try:
                return _set_attr(
                    mr, "volume_mode", V2003MultiRoomVolumeMode(payload)
                )
            except ValueError:
                return False

        if head == "e":
            try:
                return _set_attr(mr, "sleep_minutes", parse_multi_sleep(payload))
            except ValueError:
                return False

        if head == "f":
            return _set_attr(mr, "osd_on", payload == "f0")

        if head == "g":
            return _set_attr(mr, "speaker_on", payload == "g0")

        if head == "h":
            return _set_attr(mr, "mute", payload == "h0")

        return False

    def _notify(self, state: V2003ReceiverState | None) -> None:
        snapshot = copy.deepcopy(state) if state is not None else None
        for cb in list(self._subscribers):
            try:
                cb(snapshot)
            except Exception:  # pragma: no cover
                _LOGGER.exception("Subscriber callback raised")


def _set_attr(target: object, name: str, value: object) -> bool:
    """Assign ``target.name = value`` if it differs. Returns True on change."""
    if getattr(target, name) == value:
        return False
    setattr(target, name, value)
    return True
