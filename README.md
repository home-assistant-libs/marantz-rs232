# marantz-rs232

Async Python library to control Marantz AV receivers over RS232 serial, built on [serialx](https://github.com/puddly/serialx).

## Installation

```bash
pip install marantz-rs232
```

Requires Python 3.12+.

## Quick start

```python
import asyncio
from marantz_rs232 import MarantzReceiver, InputSource

async def main():
    receiver = MarantzReceiver("/dev/ttyUSB0")
    await receiver.connect()
    await receiver.query_state()

    # State is fully populated after query_state()
    print(f"Power: {receiver.state.power}")
    print(f"Volume: {receiver.state.main_zone.volume} dB")
    print(f"Input: {receiver.state.main_zone.input_source}")

    # Control the receiver
    await receiver.main.set_volume(-30.0)
    await receiver.main.select_input_source(InputSource.BD)

    await receiver.disconnect()

asyncio.run(main())
```

## CLI

A built-in CLI lets you quickly test your serial connection:

```bash
# Query and print receiver status
python -m marantz_rs232 /dev/ttyUSB0

# Also probe which input sources the receiver accepts
python -m marantz_rs232 /dev/ttyUSB0 --probe
```

## Features

### Full state after query

`connect()` only opens and verifies the serial connection. Call `query_state()` when you want the current receiver state populated into the `state` property. After that, state is kept up to date via events from the receiver.

Control lives on shared player objects:

```python
receiver.main
receiver.zone_2
receiver.zone_3
```

```python
receiver = MarantzReceiver("/dev/ttyUSB0")
await receiver.connect()
await receiver.query_state()

state = receiver.state
state.power                     # True / False (overall power)
state.main_zone.power           # True / False (main zone)
state.main_zone.volume          # float in dB (0.0 = reference, -80.0 = min, +18.0 = max)
state.main_zone.mute            # True / False
state.main_zone.input_source    # InputSource enum
state.main_zone.surround_mode   # str (e.g. "STEREO", "DOLBY DIGITAL", "DTS SURROUND")
state.main_zone.digital_input   # DigitalInputMode enum
state.main_zone.audio_decode    # AudioDecodeMode enum (AUTO / PCM / DTS)
state.main_zone.video_select    # InputSource or None
```

### Event subscription

Subscribe to state changes to react in real-time. Callbacks receive a `ReceiverState` snapshot on updates, or `None` when the connection is lost.

```python
def on_state_change(state):
    if state is None:
        print("Disconnected!")
        return
    mz = state.main_zone
    print(f"Volume: {mz.volume} dB, Source: {mz.input_source}")

unsub = receiver.subscribe(on_state_change)
# Later:
unsub()  # stop receiving events
```

### Receiver power

```python
await receiver.power_on()
await receiver.power_standby()
power = await receiver.query_power()  # bool
```

### Main zone

```python
await receiver.main.power_on()
await receiver.main.power_standby()
on = await receiver.main.query_power()  # bool
```

### Master volume

Volume is represented in dB: 0.0 dB is the reference level, -80.0 is minimum, +18.0 is maximum. Half-dB steps are supported.

```python
await receiver.main.set_volume(-25.0)     # set to -25 dB
await receiver.main.set_volume(-25.5)     # half-dB step
await receiver.main.volume_up()
await receiver.main.volume_down()
db = await receiver.main.query_volume()   # float
```

### Channel volumes

Individual channel levels, relative to the master volume. 0.0 dB is neutral, range is -12.0 to +12.0 dB. Available channels depend on the speaker configuration: FL, FR, C, SW, SL, SR, SBL, SBR, SB, FH, FW.

```python
await receiver.main.set_channel_volume("FL", 2.0)   # front left +2 dB
await receiver.main.set_channel_volume("SW", -3.5)  # subwoofer -3.5 dB
await receiver.main.channel_volume_up("C")
await receiver.main.channel_volume_down("FR")

# All channel volumes are in state after connect:
state.main_zone.channel_volumes  # {"FL": 0.0, "FR": 0.0, "C": -1.0, ...}
```

### Mute

```python
await receiver.main.mute_on()
await receiver.main.mute_off()
muted = await receiver.main.query_mute()  # bool
```

### Input source

```python
from marantz_rs232 import InputSource

await receiver.main.select_input_source(InputSource.BD)
source = await receiver.main.query_input_source()  # InputSource enum
```

Available sources depend on the model. See [Input sources](#input-sources) below.

### Surround mode

Surround mode is kept as a plain string because receivers return many combined mode names (e.g. `"DOLBY DIGITAL"`, `"DTS SURROUND"`, `"AURO3D"`).

```python
await receiver.main.set_surround_mode("STEREO")
await receiver.main.set_surround_mode("DOLBY DIGITAL")
await receiver.main.set_surround_mode("DTS SURROUND")
await receiver.main.set_surround_mode("DIRECT")
await receiver.main.set_surround_mode("PURE DIRECT")
await receiver.main.set_surround_mode("MCH STEREO")
await receiver.main.set_surround_mode("AURO3D")
mode = await receiver.main.query_surround_mode()  # str
```

### Digital input mode

```python
from marantz_rs232 import DigitalInputMode

await receiver.main.set_digital_input(DigitalInputMode.AUTO)
await receiver.main.set_digital_input(DigitalInputMode.HDMI)
await receiver.main.set_digital_input(DigitalInputMode.DIGITAL)
await receiver.main.set_digital_input(DigitalInputMode.ANALOG)
await receiver.main.set_digital_input(DigitalInputMode.EXT_IN)
await receiver.main.set_digital_input(DigitalInputMode.SEVEN_1_IN)
mode = await receiver.main.query_digital_input()  # DigitalInputMode enum or None ("NO")
```

### Audio decode

```python
from marantz_rs232 import AudioDecodeMode

await receiver.main.set_audio_decode(AudioDecodeMode.AUTO)
await receiver.main.set_audio_decode(AudioDecodeMode.PCM)
await receiver.main.set_audio_decode(AudioDecodeMode.DTS)
mode = await receiver.main.query_audio_decode()
```

### Video select

Override the video source independently from the main input source:

```python
await receiver.main.set_video_select(InputSource.DVD)
await receiver.main.cancel_video_select()  # return to following input
source = await receiver.main.query_video_select()
```

### Tone control

```python
# Tone control on/off
await receiver.main.tone_control_on()
await receiver.main.tone_control_off()

# Bass / treble: dB values from -6 to +6
await receiver.main.set_bass(3)
await receiver.main.set_treble(-2)
await receiver.main.bass_up()
await receiver.main.bass_down()
await receiver.main.treble_up()
await receiver.main.treble_down()
```

### Audyssey / EQ settings

```python
from marantz_rs232 import MultEQ, DynamicVolume, DRC

# Cinema EQ
await receiver.main.cinema_eq_on()
await receiver.main.cinema_eq_off()

# MultEQ XT/XT32
await receiver.main.set_multeq(MultEQ.AUDYSSEY)
await receiver.main.set_multeq(MultEQ.FLAT)
await receiver.main.set_multeq(MultEQ.OFF)

# Dynamic EQ
await receiver.main.dynamic_eq_on()
await receiver.main.dynamic_eq_off()

# Dynamic Volume
await receiver.main.set_dynamic_volume(DynamicVolume.MED)
await receiver.main.set_dynamic_volume(DynamicVolume.OFF)

# Dynamic Range Compression
await receiver.main.set_drc(DRC.AUTO)
await receiver.main.set_drc(DRC.HI)
```

All parameter settings are available in `state` after connect:

```python
state.main_zone.tone_control     # bool
state.main_zone.bass             # float
state.main_zone.treble           # float
state.main_zone.cinema_eq        # bool
state.main_zone.multeq           # MultEQ enum
state.main_zone.dynamic_eq       # bool
state.main_zone.dynamic_volume   # DynamicVolume enum
state.main_zone.drc              # DRC enum
```

### Sleep / ECO / Standby / Dimmer

```python
from marantz_rs232 import EcoMode, DimmerMode

# Sleep timer (minutes)
await receiver.main.set_sleep(30)
await receiver.main.sleep_off()

# ECO mode
await receiver.main.set_eco(EcoMode.AUTO)
await receiver.main.set_eco(EcoMode.ON)
await receiver.main.set_eco(EcoMode.OFF)

# Auto standby
await receiver.main.set_auto_standby("2H")
await receiver.main.auto_standby_off()

# Front-panel dimmer
await receiver.main.set_dimmer(DimmerMode.BRI)
await receiver.main.set_dimmer(DimmerMode.DIM)
await receiver.main.set_dimmer(DimmerMode.DAR)
await receiver.main.set_dimmer(DimmerMode.OFF)
```

### Tuner

```python
from marantz_rs232 import TunerBand, TunerMode

await receiver.main.set_tuner_band(TunerBand.FM)
await receiver.main.set_tuner_mode(TunerMode.AUTO)
await receiver.main.set_tuner_frequency("105000")  # FM 105.0 MHz
await receiver.main.set_tuner_preset("A1")
await receiver.main.tuner_frequency_up()
await receiver.main.tuner_frequency_down()
await receiver.main.tuner_preset_up()
await receiver.main.tuner_preset_down()

freq = await receiver.main.query_tuner_frequency()  # str
preset = await receiver.main.query_tuner_preset()   # str
```

Tuner band and mode are available in state (`state.main_zone.tuner_band`, `state.main_zone.tuner_mode`).

### Multi-zone

Zone 2 and Zone 3 can be controlled independently. Zone state (power, source, volume, mute) is populated by `query_state()` and updated via events.

```python
# Zone 2
await receiver.zone_2.power_on()
await receiver.zone_2.power_standby()
await receiver.zone_2.select_input_source(InputSource.TUNER)
await receiver.zone_2.set_volume(-30.0)
await receiver.zone_2.volume_up()
await receiver.zone_2.volume_down()
await receiver.zone_2.mute_on()
await receiver.zone_2.mute_off()

# Zone 3
await receiver.zone_3.power_on()
await receiver.zone_3.power_standby()
await receiver.zone_3.select_input_source(InputSource.CD)
await receiver.zone_3.set_volume(-35.0)
await receiver.zone_3.mute_on()
await receiver.zone_3.mute_off()
```

Zone state in `state`:

```python
state.zone_2.power           # bool
state.zone_2.input_source    # InputSource
state.zone_2.volume          # float in dB
state.zone_2.mute            # bool
state.zone_3.power           # bool
state.zone_3.input_source    # InputSource
state.zone_3.volume          # float in dB
state.zone_3.mute            # bool
```

### Source probing

Discover which input sources the receiver actually supports by trying each one:

```python
sources = await receiver.probe_sources()
# frozenset({InputSource.CD, InputSource.BD, InputSource.TUNER, ...})
```

This briefly switches through all input sources and restores the original when done. Nothing should be playing during probing.

### Connection handling

The library handles connection errors gracefully:

- If the receiver doesn't respond during `connect()`, a `ConnectionError` is raised.
- If the serial connection is lost (cable unplugged, device error), subscribers receive `None` and `connected` becomes `False`.
- Write errors during commands propagate the exception and tear down the connection.

```python
try:
    await receiver.connect()
except ConnectionError:
    print("Receiver not responding")
```

## Input sources

| Source | Protocol value |
|--------|---------------|
| `PHONO` | PHONO |
| `CD` | CD |
| `TUNER` | TUNER |
| `DVD` | DVD |
| `BD` | BD |
| `TV` | TV |
| `SAT_CBL` | SAT/CBL |
| `SAT` | SAT |
| `MPLAY` | MPLAY |
| `VCR` | VCR |
| `GAME` | GAME |
| `V_AUX` | V.AUX |
| `HDRADIO` | HDRADIO |
| `SIRIUS` | SIRIUS |
| `SIRIUSXM` | SIRIUSXM |
| `SPOTIFY` | SPOTIFY |
| `RHAPSODY` | RHAPSODY |
| `PANDORA` | PANDORA |
| `NAPSTER` | NAPSTER |
| `LASTFM` | LASTFM |
| `FLICKR` | FLICKR |
| `IRADIO` | IRADIO |
| `SERVER` | SERVER |
| `FAVORITES` | FAVORITES |
| `CDR` | CDR |
| `AUX1` - `AUX7` | AUX1-AUX7 |
| `NET` | NET |
| `NET_USB` | NET/USB |
| `BT` | BT |
| `M_XPORT` | MXPORT |
| `USB_IPOD` | USB/IPOD |

Not all sources exist on every receiver. Use `probe_sources()` to determine which sources your receiver supports.

## Serial connection

The library uses [serialx](https://github.com/puddly/serialx) for async serial communication. Marantz RS232 receivers use 9600 baud, 8 data bits, no parity, 1 stop bit (8N1) on a DB-9 connector.

## Supported models

This library implements the Marantz 2015 IP/RS232 protocol used by:

- NR1506, NR1606
- SR5010, SR6010, SR7010
- AV7702mkII

Earlier and later Marantz receivers using the same command set should also work.

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v
```

## License

MIT
