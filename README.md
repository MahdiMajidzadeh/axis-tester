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

### 1. Allow the page in Moonraker (once)

On the printer, open `moonraker.conf` (in Fluidd: *Configuration → moonraker.conf*). Add your origin to the `[authorization]` section:

```ini
[authorization]
cors_domains:
    http://localhost:8000
    http://127.0.0.1:8000
trusted_clients:
    192.168.0.0/16
    10.0.0.0/8
```

Keep any entries that are already there. If `trusted_clients` already covers your computer's IP, leave it as it is. Otherwise you can paste a Moonraker API key into the app. Restart Moonraker after saving the file.

### 2. Serve the page

You can't double-click `index.html`. A page opened as a local file sends `Origin: null`, and Moonraker blocks that.

```bash
python3 -m http.server 8000
```

Run this command in this folder, then open http://localhost:8000. Enter the address you use for Fluidd (for example `192.168.1.50`, or the full `http://…/#/` URL) and click **Connect**.

**No-config alternative:** copy `index.html` into the Fluidd web folder on the Pi (usually `~/fluidd/axis.html`) and open `http://<printer>/axis.html`. The page and Moonraker then share an origin, so you don't need `cors_domains`.

If you open Fluidd over **https**, the browser blocks this http page from calling it (mixed content). Use the no-config alternative above instead.

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
