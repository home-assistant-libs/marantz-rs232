# marantz-rs232

Async Python library to control Marantz AV receivers over RS232 serial. Supports two distinct Marantz protocols side by side:

- **Modern** (`MarantzReceiver`) — 2015 lineup using `PREFIX+VALUE\r` framing.
- **Legacy** (`MarantzLegacyReceiver`) — 2007–2010 lineup using `@CMD:VALUE\r` framing.

## Project structure

```
src/marantz_rs232/
  __init__.py    -- Public API surface for both protocols + `probe()`
  const.py       -- Modern constants and enums
  protocol.py    -- Modern wire encoding helpers
  state.py       -- Modern ReceiverState / MainZoneState / ZoneState dataclasses
  receiver.py    -- MarantzReceiver class with read loop and message dispatch
  players.py     -- MainPlayer, ZonePlayer, Zone4Player control surfaces
  probe.py       -- async probe(port) — sniffs first response byte to pick protocol
  legacy/        -- Legacy (SR7002-era) protocol implementation
    __init__.py
    const.py     -- Legacy enums (LegacyModel, LegacySource, LegacySurroundCode, ...)
    protocol.py  -- @CMD: framing, volume / tone / tuner-frequency / lip-sync codecs
    state.py     -- LegacyReceiverState / LegacyMainState / LegacyMultiRoomState
    receiver.py  -- MarantzLegacyReceiver with dispatcher across `:`, `=`, `*` separators
    players.py   -- LegacyMainPlayer + LegacyMultiRoomPlayer (separator-parameterised)
  __main__.py    -- CLI: python -m marantz_rs232 PORT [--legacy] [--detect] [--model M]

tests/
  conftest.py              -- MockSerialConnection + DEFAULT_QUERY_RESPONSES (modern)
  test_marantz_rs232.py    -- Modern receiver query/control/event/teardown tests
  test_probe.py            -- Modern source-probing tests
  test_legacy.py           -- Legacy receiver tests + per-model gating
  test_protocol_probe.py   -- probe() function tests
docs/
  Marantz 2015 NR_SR_AV IP-232 Protocol.xls
  Marantz 2007 SR7002 SR8002 RS232C Control Specification v1.00.pdf
```

## Architecture (modern receiver)

- Uses `serialx` (`open_serial_connection`) for async serial I/O (9600 baud, 8N1).
- Marantz 2015 protocol: `PREFIX + PARAM + CR (0x0D)`. Query with `PREFIX?`. Responses within ~200ms.
- `connect()` only opens/verifies the serial connection via `PW?`.
- `query_state()` fetches current receiver state (single-response via `_query()`, multi-response via fire-and-forget + `asyncio.sleep(MULTI_RESPONSE_DELAY)`).
- After querying, state is kept current via a background `_read_loop` that processes events.
- `state` property returns a deep copy of `ReceiverState`.
- Subscribers get `ReceiverState` on changes, `None` on disconnect.

## Architecture (legacy receiver)

- Same baud (9600 8N1), different framing: `@<CMD>:<VALUE>\r`. Reference: `docs/Marantz 2007 SR7002 SR8002 RS232C Control Specification v1.00.pdf`.
- Three separators in play, dispatched by the same parser/receiver: `:` (main + Multi Room A), `=` (Multi Room B, SR8002 only), `*` (HD Radio metadata, SR8002 only).
- ACK / NAK responses (`@\x06\r` / `@\x15\r`) are recognised and ignored by the read loop; status lines have shape `@CMD<sep>VALUE\r`.
- Auto-status feedback is **opt-in** on this protocol — `connect()` enables all four layers via `@AST:F\r` so subscribers see spontaneous state changes the same way they do on modern receivers.
- Set/status asymmetry: the SUR command takes `@SUR:00` to set AUTO but the receiver reports back `SUR:0`. Players add the `0` prefix on send; the parser strips it on receive.
- The HAL query intentionally returns under a different prefix (`ALS`); `_query(response_prefix="ALS")` handles the asymmetry.
- `LegacyModel.SR8002` gates Multi Room B, HD Radio metadata, Component2, HD tuner extensions. Calling those methods on a non-SR8002 model logs a warning once per feature and proceeds.
- The two receiver classes deliberately don't share inheritance — the state schemas and command sets diverge enough that a strategy-pattern unification would add complexity without value. Some duplication (subscribers, connection lifecycle) is accepted.

## Key design decisions

- `surround_mode` (modern) is `str`, not an enum — many combined mode names appear (e.g. "DOLBY DIGITAL", "DTS SURROUND", "AURO3D").
- `surround_mode` (legacy) is also a single-char `str` — see `LegacySurroundCode` for the documented codes; firmware can return others.
- Zone mute (modern) uses `Z2MU` / `Z3MU` prefixes, distinct from generic `Z2` / `Z3` zone state.
- Tuner (modern) uses `TFAN` / `TPAN` / `TMAN` prefixes (`AN` suffix indicates analog tuner band).
- Tuner (legacy) packs band into a 5-digit numeric value: `xxxxx<256` is XM channel, `<2000` is AM kHz, `>=2000` is FM in 10 kHz units.
- `_SINGLE_RESPONSE_PREFIXES` / `_MULTI_RESPONSE_PREFIXES` (modern) split queries that block on response from those that fire-and-forget.
- `probe_sources()` (modern) tries each `InputSource`, restores the original at end.
- `probe(port)` (top-level) opens the wire, sends `@PWR:?\r` then `PW?\r` back-to-back, returns the receiver class based on whether the first response byte is `@` (legacy) or `P` (modern).
- Module-level timeouts (`MULTI_RESPONSE_DELAY`, `PROBE_TIMEOUT`, `LEGACY_COMMAND_TIMEOUT`) are overridden in test modules for speed.

## Testing

- `pytest` with `pytest-asyncio`, `asyncio_mode = "auto"`.
- Modern tests use `MockSerialConnection` (`tests/conftest.py`) with `DEFAULT_QUERY_RESPONSES` keyed by 2-char prefix.
- Legacy tests use `_MockSerial` (in `tests/test_legacy.py`) with `_DEFAULT_LEGACY_RESPONSES` keyed by 3-char prefix and `@CMD:VALUE` parsing in `_on_write`.
- Run: `uv run pytest` or `python -m pytest tests/`. ~390 tests total.

## Enums

**Modern:** `InputSource`, `DigitalInputMode` (AUTO/HDMI/DIGITAL/ANALOG/EXT.IN/7.1IN), `AudioDecodeMode` (AUTO/PCM/DTS), `SurroundMode`, `EcoMode` (ON/AUTO/OFF), `DimmerMode` (BRI/DIM/DAR/OFF), `MultEQ` (AUDYSSEY/BYP.LR/FLAT/MANUAL/OFF), `DynamicVolume` (NGT/EVE/DAY/HEV/MED/LIT/OFF), `DRC` (AUTO/LOW/MID/HI/OFF), `TunerBand` (AM/FM), `TunerMode` (AUTO/MANUAL), `ZoneChannelMode`, `DialogEnhancer`, `DComp`, `MDAX`, HDMI/aspect/video enums.

**Legacy:** `LegacyModel` (GENERIC/SR7002/SR8002), `LegacyTriState`, `LegacyPower`, `LegacySource`, `LegacySurroundCode`, `LegacyTHXSet`, `LegacyEQMode`, `LegacyDolbyHeadphone`, `LegacyNightMode`, `LegacyMDAX`, `LegacyHDMIChannel`, `LegacyHDMIAudioMode`, `LegacyIPConverter`, `LegacyComponent2`, `LegacyTunerMode`, `LegacyMenu`, `LegacyCursor`, `LegacyInputAD`, `LegacyInputSignal`, `LegacyInputState`, `LegacySignalFormat`, `LegacySamplingFrequency`, `LegacyVolumeMode`, `LegacyStereoMode`, `TunerBand` (legacy variant adds XM).
