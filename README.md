# Axis Tester

A small web app that drives the X/Y axes of a Klipper 3D printer through Moonraker (the API behind Fluidd and Mainsail) and runs motion tests at different sizes, speeds and accelerations. It draws the planned path and the live nozzle position on a map of the bed, so you can hear and see where your printer starts to skip, ring or lose position.

It is made for CoreXY printers (the motor A / motor B tests assume CoreXY kinematics), but every other test works on any Cartesian printer too.

Plain HTML, CSS and JavaScript (`index.html`, `style.css`, `app.js`). No build step and no dependencies. The only extra piece is `serve.py`, a tiny Python helper that serves the files and forwards API calls to the printer.

## What it is for

- Finding the real speed and acceleration limits of your printer before you put them in `printer.cfg`.
- Checking belt tension: on a CoreXY both belts should sound and behave the same.
- Spotting skipped steps and backlash. Klipper cannot detect skipped steps by itself, but the "return to a mark" tests make them visible.
- Burning in a new build or verifying a repair.

## Caution

This app moves the printer at speeds and accelerations you choose, including values far above what you would print at. Skipped steps, a loud crash into a frame member or a loosened belt are possible outcomes of a test, and that is partly the point. Use it with care and at your own risk.

Before every session:

- **Clear the bed.** Remove prints, scrapers, tools and anything that could be hit. Keep hands, cables and cameras out of the toolhead's travel.
- **Check the limits.** The app trusts the axis limits Klipper reports. After connecting, compare **Bed X / Bed Y** and **Max vel / accel** in the Printer card with your `printer.cfg`. If they are wrong there, they are wrong here too.
- **Start small and slow.** Run **Square + diagonals** with size **Small** and speed **Slow** first. Only then increase the size, speed or acceleration or use the ramps.
- **Stay at the keyboard.** Keep the mouse near **EMERGENCY STOP** for the whole run. Tests can take minutes.
- **Mind the Z height.** The app lifts Z to at least the "Z lift" value (default 10 mm) before moving. If something on the bed is taller than that, raise the value or remove the object.
- **Only when idle.** The app refuses to start while a print is running or paused, but it does not know about things like a pending filament change. Make sure the printer is really idle.

What the app does to stay safe:

- Keeps all moves at least 5 mm inside the axis limits Klipper reports.
- Caps speed at Klipper's `max_velocity` and acceleration at `max_accel` from `printer.cfg`, and shows the values it actually used.
- Homes the printer (`G28`) first if it is not homed.
- Saves the G-code state and the current acceleration before a test and restores both afterwards, also when a test is stopped or fails.
- Sends motion in small chunks, so **Stop** takes effect within about 2–3 s.

The two stop buttons:

- **Stop** finishes the moves already queued (about 2–3 s of motion), then stops cleanly and restores the printer state.
- **EMERGENCY STOP** halts the printer immediately (Klipper shutdown). Use it when something is about to hit. Afterwards click **Firmware restart** and home the printer again.

## How to use

### 1. Start the server

In this folder, run:

```bash
python3 serve.py
```

Then open http://localhost:8000. Python 3 is all you need; the script uses only the standard library.

Why the server: the browser only talks to `localhost`, and `serve.py` forwards the API calls to the printer. That way `moonraker.conf` on the printer needs no changes. This matters on Creality printers (K1, K2), where `moonraker.conf` cannot be edited from Fluidd.

### 2. Connect

Enter the address you use for Fluidd (for example `192.168.1.103:4408`, or the full `http://…/#/` URL) and click **Connect**. The status pill turns green when Klipper is ready.

If Moonraker asks for a login, either add your computer's IP to `trusted_clients` in `moonraker.conf` or paste an API key into the app.

### 3. Pick a test and set it up

- **Test**: choose one from the list. The blue box below the list says what to look and listen for.
- **Size**: the presets are fractions of the usable bed (Small 25 %, Medium 50 %, Large 100 %, Wide and Tall), or type an X/Y size and center. The area is clamped to stay inside the safe limits.
- **Speed**: presets from Slow (30 mm/s) to Max (`max_velocity`), or type a value. **Accel** left blank keeps the printer's current acceleration.
- **Repeats** runs the pattern several times. **Z lift** is the height the nozzle is raised to before any move.
- Some tests have extra fields (number of turns, points, step size, start and end speed, and so on).

The lines under the fields show the effective area, speed range, acceleration, number of moves and estimated time. A yellow line means a value was capped or something needs attention.

### 4. Run

Click **Run test**, check the summary dialog, then **Run**. While a test runs:

- the map shows the planned path (colour = speed, orange = motor A only, purple = motor B only) and the white live trail,
- the progress line shows how much motion has been queued,
- **Stop** and **EMERGENCY STOP** are active in the header.

Some tests pause and ask you to mark the nozzle position (a piece of tape with a pen dot works). Do it quickly: if Klipper's `idle_timeout` turns the motors off while you wait, the test aborts.

### The tests

| Test | What it does | What to look for |
|---|---|---|
| Square + diagonals | Traces the rectangle, then corner-to-corner diagonals, then 45° strokes that move **only motor A** or **only motor B** | The rectangle closes exactly at its start corner. Motors A and B sound and vibrate about the same |
| Speed ramp | Moves along one line (X, Y, A or B) back and forth while the speed steps up | The first speed where the printer grinds, clicks or shifts position is your limit |
| Circle / ellipse | Draws a circle from many short line segments, so it works without `[gcode_arcs]` | The path is smooth, with no flat spots or clunks |
| Zig-zag | Rows and/or columns with sharp direction reversals | The frame doesn't rock and the head returns to its start |
| Random points + return | Moves to random points, then returns to a reference point you marked | The nozzle lines up with your mark. **Klipper can't detect skipped steps, but this test can** |
| Acceleration ramp | Moves along one line at a fixed speed while the acceleration steps up | The first acceleration that thuds, clicks or shifts the head is your limit |
| Star (all angles) | Draws spokes out from the center every 10–45°. Each angle uses a different mix of motors A and B | Every spoke is straight and sounds about the same |
| Spiral | Spirals outward, then back inward | Smooth, even sound with no buzz at any particular radius |
| Backlash / repeatability | Reaches one target point from 4 or 8 directions, pausing there each time | The nozzle stops on your mark from every direction |

### Free mode

Click **Free mode** above the map, then click anywhere on the map and the nozzle moves there at the free-mode speed. A crosshair shows the exact X/Y before you click. Clicks are ignored until the nozzle arrives.

Free mode also has jog buttons for X/Y (1, 10 or 50 mm, or the arrow keys) and buttons for the center and the four corners. Moves stay inside the safe area. The printer is homed first if needed, and Z is lifted the same way as for the tests.

### Printer card

**Home all (G28)**, **Go to center** and **Motors off (M84)** work any time the printer is idle. The stats show the Klipper state, kinematics, homed axes, bed limits, speed and acceleration limits, live position and job state.

## Running without serve.py

The app itself is static, so any web server (nginx, `npx serve`, a NAS, the printer itself) can host the three files. The browser then calls Moonraker directly, and Moonraker has to allow the page's origin. Add it to `moonraker.conf` and restart Moonraker:

```ini
[authorization]
cors_domains:
    http://localhost:8000
```

Two limits apply:

- You cannot double-click `index.html`. A page opened as a local file sends `Origin: null`, and Moonraker always blocks that.
- An HTTPS host (GitHub Pages, for example) cannot talk to a plain-HTTP Moonraker; browsers block mixed content. Use HTTP hosting, or put Moonraker behind HTTPS.

## Try it without a printer

`mock/mock_moonraker.py` is a fake Moonraker for testing the UI:

```bash
python3 mock/mock_moonraker.py
```

Then connect the app to `127.0.0.1:7125`. To simulate a print in progress, open `http://127.0.0.1:7125/mock/set?print=printing` in your browser (`?print=standby` sets it back).

## First run on real hardware

1. After you connect, check that **Bed X / Bed Y** and **Max vel / accel** match your `printer.cfg`.
2. Run **Square + diagonals** with size **Small** and speed **Slow**. Keep a hand near EMERGENCY STOP.
3. Only after that, increase the size and speed or use the ramps.
