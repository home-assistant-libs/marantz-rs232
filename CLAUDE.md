# marantz-rs232

Async Python library to control Marantz AV receivers over RS232 serial. Supports two distinct Marantz protocols side by side, named after the year of their reference spec PDF:

- **v2015** (`MarantzV2015Receiver`) — 2015 lineup using `PREFIX+VALUE\r` framing.
- **v2007** (`MarantzV2007Receiver`) — 2007–2010 lineup (SR7002/SR8002-era) using `@CMD:VALUE\r` framing.

A third protocol is documented but not yet implemented:
- **v2003** — 2003-era SR9300/SR8300 using `@<ID><CODE>\r` positional framing at 4800 baud with RTS/CTS hardware flow control. See `docs/Marantz 2003 SR9300 SR8300 RS232C Control Specification v2.00.pdf`.

All public symbols are prefixed with `V2007` or `V2015` to keep the two side-by-side namespaces clean and to leave room for `V2003`.

## Project structure

```
src/marantz_rs232/
  __init__.py    -- Public API surface re-exporting both protocols + `probe()`
  probe.py       -- async probe(port) — sniffs first response byte to pick protocol
  __main__.py    -- CLI: python -m marantz_rs232 PORT [--legacy] [--detect] [--model M]
  v2015/         -- Modern (2015-era) protocol implementation
    __init__.py
    const.py     -- V2015 constants and enums (V2015InputSource, V2015SurroundMode, ...)
    protocol.py  -- Modern wire encoding helpers
    state.py     -- V2015ReceiverState / V2015MainZoneState / V2015ZoneState dataclasses
    receiver.py  -- MarantzV2015Receiver class with read loop and message dispatch
    players.py   -- V2015MainPlayer, V2015ZonePlayer, V2015Zone4Player
  v2007/         -- Legacy (SR7002-era) protocol implementation
    __init__.py
    const.py     -- V2007 enums (V2007Model, V2007Source, V2007SurroundCode, ...)
    protocol.py  -- @CMD: framing, volume / tone / tuner-frequency / lip-sync codecs
    state.py     -- V2007ReceiverState / V2007MainState / V2007MultiRoomState
    receiver.py  -- MarantzV2007Receiver with dispatcher across `:`, `=`, `*` separators
    players.py   -- V2007MainPlayer + V2007MultiRoomPlayer (separator-parameterised)

tests/
  conftest.py            -- MockSerialConnection + DEFAULT_QUERY_RESPONSES (v2015)
  test_v2015.py          -- v2015 receiver query/control/event/teardown tests
  test_probe.py          -- v2015 source-probing tests
  test_v2007.py          -- v2007 receiver tests + per-model gating
  test_protocol_probe.py -- probe() function tests
docs/
  Marantz 2015 NR_SR_AV IP-232 Protocol.xls
  Marantz 2007 SR7002 SR8002 RS232C Control Specification v1.00.pdf
  Marantz 2003 SR9300 SR8300 RS232C Control Specification v2.00.pdf
```

## Architecture (v2015 receiver)

- Uses `serialx` (`open_serial_connection`) for async serial I/O (9600 baud, 8N1).
- Marantz 2015 protocol: `PREFIX + PARAM + CR (0x0D)`. Query with `PREFIX?`. Responses within ~200ms.
- `connect()` only opens/verifies the serial connection via `PW?`.
- `query_state()` fetches current receiver state (single-response via `_query()`, multi-response via fire-and-forget + `asyncio.sleep(V2015_MULTI_RESPONSE_DELAY)`).
- After querying, state is kept current via a background `_read_loop` that processes events.
- `state` property returns a deep copy of `V2015ReceiverState`.
- Subscribers get `V2015ReceiverState` on changes, `None` on disconnect.

## Architecture (v2007 receiver)

- Same baud (9600 8N1), different framing: `@<CMD>:<VALUE>\r`. Reference: `docs/Marantz 2007 SR7002 SR8002 RS232C Control Specification v1.00.pdf`.
- Three separators in play, dispatched by the same parser/receiver: `:` (main + Multi Room A), `=` (Multi Room B, SR8002 only), `*` (HD Radio metadata, SR8002 only).
- ACK / NAK responses (`@\x06\r` / `@\x15\r`) are recognised and ignored by the read loop; status lines have shape `@CMD<sep>VALUE\r`.
- Auto-status feedback is **opt-in** on this protocol — `connect()` enables all four layers via `@AST:F\r` so subscribers see spontaneous state changes the same way they do on v2015 receivers.
- Set/status asymmetry: the SUR command takes `@SUR:00` to set AUTO but the receiver reports back `SUR:0`. Players add the `0` prefix on send; the parser strips it on receive.
- The HAL query intentionally returns under a different prefix (`ALS`); `_query(response_prefix="ALS")` handles the asymmetry.
- `V2007Model.SR8002` gates Multi Room B, HD Radio metadata, Component2, HD tuner extensions. Calling those methods on a non-SR8002 model logs a warning once per feature and proceeds.
- The two receiver classes deliberately don't share inheritance — the state schemas and command sets diverge enough that a strategy-pattern unification would add complexity without value. Some duplication (subscribers, connection lifecycle) is accepted.

## Key design decisions

- `surround_mode` (v2015) is `str`, not an enum — many combined mode names appear (e.g. "DOLBY DIGITAL", "DTS SURROUND", "AURO3D").
- `surround_mode` (v2007) is also a single-char `str` — see `V2007SurroundCode` for the documented codes; firmware can return others.
- Zone mute (v2015) uses `Z2MU` / `Z3MU` prefixes, distinct from generic `Z2` / `Z3` zone state.
- Tuner (v2015) uses `TFAN` / `TPAN` / `TMAN` prefixes (`AN` suffix indicates analog tuner band).
- Tuner (v2007) packs band into a 5-digit numeric value: `xxxxx<256` is XM channel, `<2000` is AM kHz, `>=2000` is FM in 10 kHz units.
- `_V2015_SINGLE_RESPONSE_PREFIXES` / `_V2015_MULTI_RESPONSE_PREFIXES` split queries that block on response from those that fire-and-forget.
- `probe_sources()` (v2015) tries each `V2015InputSource`, restores the original at end.
- `probe(port)` (top-level) opens the wire, sends `@PWR:?\r` then `PW?\r` back-to-back, returns the receiver class based on whether the first response byte is `@` (v2007) or `P` (v2015).
- Module-level timeouts (`V2015_MULTI_RESPONSE_DELAY`, `V2015_PROBE_TIMEOUT`, `V2007_COMMAND_TIMEOUT`) are overridden in test modules for speed.

## Testing

- `pytest` with `pytest-asyncio`, `asyncio_mode = "auto"`.
- v2015 tests use `MockSerialConnection` (`tests/conftest.py`) with `DEFAULT_QUERY_RESPONSES` keyed by 2-char prefix.
- v2007 tests use `_MockSerial` (in `tests/test_v2007.py`) with `_DEFAULT_V2007_RESPONSES` keyed by 3-char prefix and `@CMD:VALUE` parsing in `_on_write`.
- Run: `uv run pytest` or `python -m pytest tests/`. ~397 tests total.

## Enums

**v2015:** `V2015InputSource`, `V2015DigitalInputMode` (AUTO/HDMI/DIGITAL/ANALOG/EXT.IN/7.1IN), `V2015AudioDecodeMode` (AUTO/PCM/DTS), `V2015SurroundMode`, `V2015EcoMode` (ON/AUTO/OFF), `V2015DimmerMode` (BRI/DIM/DAR/OFF), `V2015MultEQ` (AUDYSSEY/BYP.LR/FLAT/MANUAL/OFF), `V2015DynamicVolume` (NGT/EVE/DAY/HEV/MED/LIT/OFF), `V2015DRC` (AUTO/LOW/MID/HI/OFF), `V2015TunerBand` (AM/FM), `V2015TunerMode` (AUTO/MANUAL), `V2015ZoneChannelMode`, `V2015DialogEnhancer`, `V2015DComp`, `V2015MDAX`, HDMI/aspect/video enums.

**v2007:** `V2007Model` (GENERIC/SR7002/SR8002), `V2007TriState`, `V2007Power`, `V2007Source`, `V2007SurroundCode`, `V2007THXSet`, `V2007EQMode`, `V2007DolbyHeadphone`, `V2007NightMode`, `V2007MDAX`, `V2007HDMIChannel`, `V2007HDMIAudioMode`, `V2007IPConverter`, `V2007Component2`, `V2007TunerMode`, `V2007Menu`, `V2007Cursor`, `V2007InputAD`, `V2007InputSignal`, `V2007InputState`, `V2007SignalFormat`, `V2007SamplingFrequency`, `V2007VolumeMode`, `V2007StereoMode`, `V2007TunerBand` (adds XM).
