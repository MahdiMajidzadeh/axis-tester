# Axis Tester

A single-file web app (`index.html`) that connects to a Klipper printer through Moonraker (the API behind Fluidd) and runs X/Y motion tests at different sizes and speeds. It's made for CoreXY printers.

## Tests

| Test | What it does | What to look for |
|---|---|---|
| Square + diagonals | Traces the rectangle, then corner-to-corner diagonals, then 45° strokes that move **only motor A** or **only motor B** | The rectangle closes exactly at its start corner. Motors A and B sound and vibrate about the same |
| Speed ramp | Moves along one line (X, Y, A or B) back and forth while the speed steps up | The first speed where the printer grinds, clicks or shifts position is your limit |
| Circle / ellipse | Draws a circle from many short line segments, so it works without `[gcode_arcs]` | The path is smooth, with no flat spots or clunks |
| Zig-zag | Rows and/or columns with sharp direction reversals | The frame doesn't rock and the head returns to its start |
| Random points + return | Moves to random points, then returns to a reference point you marked | The nozzle lines up with your mark. **Klipper can't detect skipped steps, but this test can** |

Every run:
- refuses to start while a print is running or paused
- homes the printer (`G28`) if it isn't homed
- lifts Z (default 10 mm)
- keeps moves inside the bed limits Klipper reports
- caps speed at `max_velocity` and acceleration at `max_accel`, and shows the values it actually used
- saves the printer's G-code state and acceleration before the test and restores them afterwards

**Stop** halts motion after about 2–3 s, once the moves already queued have run. **EMERGENCY STOP** halts the printer immediately. After an emergency stop, click **Firmware restart** and home the printer again.

## Setup

In this folder, run:

```bash
python3 serve.py
```

Open http://localhost:8000. Enter the address you use for Fluidd (for example `192.168.1.103:4408`, or the full `http://…/#/` URL) and click **Connect**.

`serve.py` (Python standard library only) serves the page and forwards the API calls to the printer. The browser only ever talks to `localhost`, so you don't need to change anything on the printer. This matters on Creality printers (K1, K2), where `moonraker.conf` isn't editable from Fluidd.

If Moonraker asks for a login, either add your computer's IP to `trusted_clients` or paste an API key into the app.

### Without serve.py

You can also serve `index.html` any other way, but then the browser calls Moonraker directly, and Moonraker has to allow the page's origin. Add the origin to the `[authorization]` section of `moonraker.conf`, then restart Moonraker:

```ini
[authorization]
cors_domains:
    http://localhost:8000
```

You can't double-click `index.html`. A page opened as a local file sends `Origin: null`, and Moonraker always blocks that.

## Try it without a printer

`mock/mock_moonraker.py` is a fake Moonraker for testing the UI:

```bash
python3 mock/mock_moonraker.py
```

Then connect the app to `127.0.0.1:7125`. To simulate a print in progress, open `http://127.0.0.1:7125/mock/set?print=printing` in your browser.

## First run on real hardware

1. After you connect, check that **Bed X / Bed Y** and **Max vel / accel** match your `printer.cfg`.
2. Run **Square + diagonals** with size **Small** and speed **Slow**. Keep a hand near EMERGENCY STOP.
3. Only after that, increase the size and speed or use the speed ramp.
