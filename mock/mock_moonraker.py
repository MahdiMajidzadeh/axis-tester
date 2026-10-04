#!/usr/bin/env python3
"""Minimal fake Moonraker for testing index.html. Port 7125.
Control: GET /mock/set?print=printing|standby&homed=xyz|&state=ready|shutdown
"""
import json, math, re, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

LOCK = threading.Lock()
ST = {
    "state": "ready", "homed": "", "print": "standby",
    "pos": [117.0, 117.0, 0.0], "f": 3000.0, "absolute": True,
    "max_velocity": 250.0, "max_accel": 3000.0, "saved": {},
    "queue": [],  # (t0, t1, p0, p1)
    "gcode_log": [],
}
AMIN = [0.0, 0.0, 0.0, 0.0]
AMAX = [235.0, 235.0, 250.0, 0.0]


def end_time():
    q = ST["queue"]
    return max(time.time(), q[-1][1]) if q else time.time()


def live():
    now = time.time()
    q = ST["queue"]
    while q and q[0][1] < now:
        q.pop(0)
    if not q:
        return list(ST["pos"])
    t0, t1, p0, p1 = q[0]
    if now < t0:
        return list(p0)
    k = (now - t0) / max(t1 - t0, 1e-9)
    return [p0[i] + (p1[i] - p0[i]) * k for i in range(3)]


def add_move(target, v):
    p0 = list(ST["pos"])
    d = math.dist(p0, target)
    t0 = end_time()
    t1 = t0 + d / max(v, 1e-6) + 0.02
    ST["queue"].append((t0, t1, p0, list(target)))
    ST["pos"] = list(target)


class Err(Exception):
    pass


def run_line(line):
    line = line.split(";")[0].strip()
    if not line:
        return
    ST["gcode_log"].append(line)
    if ST["state"] != "ready":
        raise Err("Klipper not ready")
    cmd = line.split()[0].upper()
    params = dict((m[0].upper(), m[1:]) for m in line.split()[1:])
    if cmd in ("G0", "G1"):
        if "E" in params:
            raise Err("mock: E not expected")
        if "F" in params:
            ST["f"] = float(params["F"])
        tgt = list(ST["pos"])
        for i, ax in enumerate("XYZ"):
            if ax in params:
                if ax.lower() not in ST["homed"]:
                    raise Err("Must home axis first: %s" % line)
                val = float(params[ax])
                tgt[i] = val if ST["absolute"] else tgt[i] + val
                if tgt[i] < AMIN[i] or tgt[i] > AMAX[i]:
                    raise Err("Move out of range: %.3f %.3f %.3f [0.000]" % tuple(tgt))
        v = min(ST["f"] / 60.0, ST["max_velocity"])
        add_move(tgt, v)
    elif cmd == "G28":
        ST["queue"].clear()
        time.sleep(1.0)
        ST["pos"] = [235.0, 235.0, 0.0]
        ST["homed"] = "xyz"
    elif cmd == "G90":
        ST["absolute"] = True
    elif cmd == "G91":
        ST["absolute"] = False
    elif cmd == "G4":
        t0 = end_time()
        ms = float(params.get("P", 0))
        ST["queue"].append((t0, t0 + ms / 1000, list(ST["pos"]), list(ST["pos"])))
    elif cmd == "M400":
        LOCK.release()
        try:
            while end_time() > time.time() + 0.01:
                if ST["state"] != "ready":
                    break
                time.sleep(0.05)
        finally:
            LOCK.acquire()
        if ST["state"] != "ready":
            raise Err("Klipper shutdown")
    elif cmd == "M84":
        ST["homed"] = ""
    elif cmd == "SAVE_GCODE_STATE":
        ST["saved"][params.get("NAME=axistest", "x")] = (ST["absolute"], ST["f"])
    elif cmd == "RESTORE_GCODE_STATE":
        pass
    elif cmd == "SET_VELOCITY_LIMIT":
        m = re.search(r"ACCEL=([\d.]+)", line)
        if m:
            ST["max_accel"] = float(m.group(1))
    else:
        raise Err("Unknown command:\"%s\"" % cmd)
    # emulate Klipper's lookahead stall: block when >2s of motion is buffered
    LOCK.release()
    try:
        while end_time() - time.time() > 2.0 and ST["state"] == "ready":
            time.sleep(0.05)
    finally:
        LOCK.acquire()
    if ST["state"] != "ready":
        raise Err("Klipper shutdown")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def cors(self):
        o = self.headers.get("Origin")
        if o and o != "null":
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Api-Key")

    def send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def err(self, code, msg):
        self.send(code, {"error": {"code": code, "message": msg}})

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query, keep_blank_values=True)
        if u.path == "/printer/info":
            msg = {"ready": "Printer is ready", "shutdown": "Emergency stop\nOnce the underlying issue is corrected, use the\n\"FIRMWARE_RESTART\" command to reset the firmware", "startup": "Klipper starting"}[ST["state"]]
            return self.send(200, {"result": {"state": ST["state"], "state_message": msg, "hostname": "mock"}})
        if u.path == "/printer/objects/query":
            if ST["state"] != "ready":
                return self.err(503, "Klippy Host not connected")
            with LOCK:
                lp = live() + [0.0]
                st = {
                    "toolhead": {"homed_axes": ST["homed"], "axis_minimum": AMIN, "axis_maximum": AMAX,
                                 "position": ST["pos"] + [0.0], "max_velocity": ST["max_velocity"], "max_accel": ST["max_accel"]},
                    "print_stats": {"state": ST["print"]},
                    "motion_report": {"live_position": lp},
                }
                if "configfile" in q:
                    st["configfile"] = {"settings": {"printer": {"kinematics": "corexy", "max_velocity": 250.0, "max_accel": 3000.0}}}
            return self.send(200, {"result": {"eventtime": time.time(), "status": st}})
        if u.path == "/mock/set":
            for k, key in (("print", "print"), ("homed", "homed"), ("state", "state")):
                if k in q:
                    ST[key] = q[k][0]
            if "homed" in q and q["homed"] == [""]:
                ST["homed"] = ""
            return self.send(200, {"result": {k: ST[k] for k in ("state", "homed", "print")}})
        if u.path == "/mock/gcode":
            return self.send(200, {"result": ST["gcode_log"][-200:]})
        return self.err(404, "Not found")

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        if u.path == "/printer/gcode/script":
            script = body.get("script") or parse_qs(u.query).get("script", [""])[0]
            with LOCK:
                try:
                    for line in script.split("\n"):
                        run_line(line)
                except Err as e:
                    return self.err(400, str(e))
            return self.send(200, {"result": "ok"})
        if u.path == "/printer/emergency_stop":
            # no LOCK: must work while a gcode request is in flight
            ST["state"] = "shutdown"
            ST["homed"] = ""
            ST["queue"].clear()
            return self.send(200, {"result": "ok"})
        if u.path == "/printer/firmware_restart":
            ST["state"] = "startup"
            def back():
                time.sleep(1.5)
                ST["state"] = "ready"
                ST["max_accel"] = 3000.0
            threading.Thread(target=back, daemon=True).start()
            return self.send(200, {"result": "ok"})
        return self.err(404, "Not found")


if __name__ == "__main__":
    print("mock moonraker on :7125")
    ThreadingHTTPServer(("127.0.0.1", 7125), H).serve_forever()
