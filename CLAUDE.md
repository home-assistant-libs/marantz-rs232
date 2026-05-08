# marantz-rs232

Async Python library to control Marantz AV receivers over RS232 serial.

## Project structure

```
src/marantz_rs232/
  __init__.py    -- Public API: enums, ReceiverState, MarantzReceiver class
  const.py       -- Constants and enums
  protocol.py    -- Volume/parameter encoding helpers
  state.py       -- ReceiverState / MainZoneState / ZoneState dataclasses
  receiver.py    -- MarantzReceiver class with read loop and message dispatch
  players.py     -- MainPlayer, ZonePlayer control surfaces
  __main__.py    -- CLI: python -m marantz_rs232 PORT [--probe]

tests/
  conftest.py             -- MockSerialConnection, fixtures (receiver, mock_serial), DEFAULT_QUERY_RESPONSES
  test_marantz_rs232.py   -- Query, control, event, and teardown tests
  test_probe.py           -- Source probing tests
```

## Architecture

- Uses `serialx` (`open_serial_connection`) for async serial I/O (9600 baud, 8N1).
- Marantz RS232 protocol: `PREFIX + PARAM + CR (0x0D)`. Query with `PREFIX?`. Responses within ~200ms.
- `connect()` only opens/verifies the serial connection via `PW?`.
- `query_state()` fetches current receiver state (single-response via `_query()`, multi-response via fire-and-forget + `asyncio.sleep(MULTI_RESPONSE_DELAY)`).
- After querying, state is kept current via a background `_read_loop` that processes events.
- `state` property returns a deep copy of `ReceiverState`.
- Subscribers get `ReceiverState` on changes, `None` on disconnect.

## Key design decisions

- `surround_mode` is `str`, not an enum -- many combined mode names appear (e.g. "DOLBY DIGITAL", "DTS SURROUND", "AURO3D").
- Zone mute uses `Z2MU` / `Z3MU` prefixes, distinct from generic `Z2` / `Z3` zone state.
- Tuner uses `TFAN` / `TPAN` / `TMAN` prefixes (Marantz protocol; the `AN` suffix indicates analog tuner band).
- `_SINGLE_RESPONSE_PREFIXES` use `_query()` (blocks waiting for response). `_MULTI_RESPONSE_PREFIXES` use fire-and-forget + sleep.
- Video select: `SOURCE` / `OFF` response maps to `None` state. Separate `cancel_video_select` for sending SOURCE command.
- `probe_sources()` uses `_send_and_wait()` to try each `InputSource`, restores original at end.
- Module-level constants `MULTI_RESPONSE_DELAY`, `PROBE_TIMEOUT` are overridden in `tests/conftest.py` for speed.

## Testing

- `pytest` with `pytest-asyncio`, `asyncio_mode = "auto"`.
- `MockSerialConnection` uses a real `asyncio.StreamReader` with a mock writer. `_on_write` synchronously feeds responses into the reader for queries (`_query_responses` dict) and calls `_command_handler` for set commands.
- `DEFAULT_QUERY_RESPONSES` provides startup responses for all prefixes. Cleared after `connect()` in the `receiver` fixture so individual tests control responses.
- Run: `uv run pytest` or `python -m pytest tests/`

## Enums

`InputSource`, `DigitalInputMode` (AUTO/HDMI/DIGITAL/ANALOG/EXT.IN/7.1IN), `AudioDecodeMode` (AUTO/PCM/DTS), `SurroundMode`, `EcoMode` (ON/AUTO/OFF), `DimmerMode` (BRI/DIM/DAR/OFF), `MultEQ` (AUDYSSEY/BYP.LR/FLAT/MANUAL/OFF), `DynamicVolume` (NGT/EVE/DAY/HEV/MED/LIT/OFF), `DRC` (AUTO/LOW/MID/HI/OFF), `TunerBand` (AM/FM), `TunerMode` (AUTO/MANUAL).

## Protocol reference

Protocol derived from `Marantz 2015 NR_SR_AV IP-232 Protocol.xls` covering NR1506, NR1606, SR5010, SR6010, SR7010, AV7702mkII.
