#!/usr/bin/env python3
"""
WiZ Connected Smart Philips Bulb Multi-Device Controller
Supports controlling multiple WiZ bulbs:
- Yash's Room Lamp (A60 RGBW Color Bulb)
- Yash's Room Main Light (Tunable White T-Bulb)
- Nilesh's Room Light (Tunable White T-Bulb)

Features:
- Direct local UDP control (on, off, dim, Kelvin, RGB colors, dynamic scenes, scan)
- Ambient AI Status Signaling (Blue for input, Red for error, Green for success, Warm for default)
- Strobe emergency alert modes
"""

import socket
import json
import os
import sys
import argparse
import concurrent.futures
import time
import signal
import subprocess

UDP_PORT = 38899
CONFIG_FILE = os.path.expanduser("~/.agents/skills/wiz-bulb/config.json")
PID_FILE = os.path.expanduser("~/.agents/skills/wiz-bulb/alert.pid")

DEFAULT_CONFIG = {
    "default_target": "yash",
    "bulbs": {
        "lamp": {
            "name": "Yash's Room Lamp (A60)",
            "owner": "Yash",
            "room": "Yash's Room",
            "type": "A60 RGBW Color",
            "ip": "192.168.1.6",
            "mac": "9877d564d590",
            "module": "ESP25_SHRGB_01",
            "fwVersion": "1.38.0"
        },
        "yash": {
            "name": "Yash's Room Main Light",
            "owner": "Yash",
            "room": "Yash's Room",
            "type": "Tunable White T-Bulb",
            "ip": "192.168.1.17",
            "mac": "9877d5b65b60",
            "module": "ESP25_SHTW_01",
            "fwVersion": "1.39.0"
        },
        "nilesh": {
            "name": "Nilesh's Room",
            "owner": "Nilesh",
            "room": "Nilesh's Room",
            "type": "Tunable White T-Bulb",
            "ip": "192.168.1.16",
            "mac": "d8a011c074ef",
            "module": "ESP01_SHTW1C_31",
            "fwVersion": "1.35.0"
        }
    }
}

NAMED_COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "cyan": (0, 255, 255),
    "purple": (128, 0, 128),
    "magenta": (255, 0, 255),
    "yellow": (255, 200, 0),
    "orange": (255, 100, 0),
    "pink": (255, 105, 180),
    "violet": (138, 43, 226),
}

SCENES = {
    "ocean": 1,
    "romance": 2,
    "sunset": 3,
    "party": 4,
    "fireplace": 5,
    "cozy": 6,
    "forest": 7,
    "pastel": 8,
    "candlelight": 9,
    "golden": 10,
    "golden_white": 10,
    "pulse": 11,
    "steampunk": 12,
    "warm_white": 13,
    "warm": 13,
    "daylight": 14,
    "cool_white": 15,
    "cool": 15,
    "night_light": 16,
    "nightlight": 16,
    "focus": 29,
    "relax": 30,
    "true_colors": 31,
    "tv_time": 18,
    "plantgrowth": 32,
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG

def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Warning: could not save config: {e}", file=sys.stderr)

def send_udp(ip, payload, timeout=1.5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(json.dumps(payload).encode("utf-8"), (ip, UDP_PORT))
        data, _ = sock.recvfrom(2048)
        return json.loads(data.decode("utf-8"))
    except socket.timeout:
        return None
    except Exception:
        return None
    finally:
        sock.close()

def build_pilot_payload(params):
    return {"method": "setPilot", "params": params}

def stop_background_alert(quiet=True):
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            if not quiet:
                print(f"Stopped running alert process (PID {pid}).")
        except ProcessLookupError:
            pass
        except Exception as e:
            if not quiet:
                print(f"Notice: {e}")
        finally:
            if os.path.exists(PID_FILE):
                try:
                    os.remove(PID_FILE)
                except Exception:
                    pass

def scan_network():
    local_ip = "192.168.1.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    subnet_prefix = ".".join(local_ip.split(".")[:3])
    found = {}

    def check_ip(ip):
        res = send_udp(ip, {"method": "getPilot"}, timeout=0.35)
        if res and "result" in res:
            return ip, res["result"]
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(check_ip, f"{subnet_prefix}.{i}") for i in range(1, 255)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                ip, data = res
                found[ip] = data

    return found

def resolve_target_bulbs(target_key, auto_recover=True):
    cfg = load_config()
    bulbs = cfg.get("bulbs", {})
    target_key = (target_key or cfg.get("default_target", "yash")).lower()

    if target_key in ("all", "both"):
        selected = list(bulbs.items())
    elif target_key in ("myroom", "room", "yash-all"):
        selected = [(k, v) for k, v in bulbs.items() if v.get("owner", "").lower() == "yash"]
    elif target_key in ("main", "ceiling", "tbulb", "t-bulb", "t_bulb", "mainlight"):
        selected = [("yash", bulbs.get("yash", {}))]
    elif target_key in bulbs:
        selected = [(target_key, bulbs[target_key])]
    else:
        matched = False
        for k, v in bulbs.items():
            if v.get("ip") == target_key:
                selected = [(k, v)]
                matched = True
                break
        if not matched:
            selected = [(target_key, {"name": f"Bulb ({target_key})", "ip": target_key})]

    verified = []
    rescanned_devices = None
    config_changed = False

    for b_id, b_info in selected:
        ip = b_info.get("ip")
        mac = b_info.get("mac")
        resp = send_udp(ip, {"method": "getPilot"}, timeout=0.8)
        if resp and "result" in resp:
            verified.append((b_id, b_info))
            continue

        if auto_recover and mac:
            if rescanned_devices is None:
                rescanned_devices = scan_network()
            new_ip = None
            for dev_ip, dev_res in rescanned_devices.items():
                if dev_res.get("mac") == mac:
                    new_ip = dev_ip
                    break
            if new_ip:
                print(f"[{b_info.get('name', b_id)}] Reconnected to new IP: {new_ip}", file=sys.stderr)
                b_info["ip"] = new_ip
                if b_id in cfg.get("bulbs", {}):
                    cfg["bulbs"][b_id]["ip"] = new_ip
                    config_changed = True
                verified.append((b_id, b_info))
                continue

        verified.append((b_id, b_info))

    if config_changed:
        save_config(cfg)

    return verified

def get_bulb_status(ip):
    resp = send_udp(ip, {"method": "getPilot"})
    if not resp or "result" not in resp:
        return None
    res = resp["result"]
    state = "ON" if res.get("state") else "OFF"
    dimming = res.get("dimming", 100)
    temp = res.get("temp", "N/A")
    scene_id = res.get("sceneId", "None")
    rssi = res.get("rssi", "N/A")
    r = res.get("r")
    g = res.get("g")
    b = res.get("b")
    rgb_str = f"RGB({r},{g},{b})" if r is not None and g is not None and b is not None else None
    return {
        "ip": ip,
        "mac": res.get("mac", ""),
        "state": state,
        "dimming": dimming,
        "temp": temp,
        "rgb": rgb_str,
        "sceneId": scene_id,
        "rssi": rssi,
        "raw": res,
    }

def set_bulb_pilot(b_info, params):
    ip = b_info["ip"]
    payload = build_pilot_payload(params)
    resp = send_udp(ip, payload)
    if resp and resp.get("result", {}).get("success"):
        return True, resp["result"]
    return False, resp

def execute_action(target_key, action_fn, action_name, stop_alert=True):
    if stop_alert:
        stop_background_alert(quiet=True)
    targets = resolve_target_bulbs(target_key)
    results = {}
    for b_id, b_info in targets:
        name = b_info.get("name", b_id)
        ip = b_info["ip"]
        success, details = action_fn(b_info)
        results[name] = success
        status_text = "Done" if success else "Failed (Bulb rejected or unreachable)"
        print(f"[{name} @ {ip}]: {action_name} -> {status_text}")
    return results

def handle_ambient_signal(signal_name, duration=10):
    """
    Ambient status signaling on Yash's Room Lamp (A60).
    Rule:
    - Only operates if the Lamp is currently ON.
    - Preserves whatever dimming level is currently set.
    - 'blue' (help/confirmation): sets Lamp to Blue.
    - 'red' (issue/error): sets Lamp to Red.
    - 'green' (success/done): sets Lamp to Green for `duration` seconds, then reverts to default Warm White.
    - 'warm' / 'default': reverts Lamp to default Warm White (2700K).
    """
    cfg = load_config()
    lamp_info = cfg.get("bulbs", {}).get("lamp")
    if not lamp_info:
        return False, "Lamp not found in config"

    st = get_bulb_status(lamp_info["ip"])
    if not st or st["state"] != "ON":
        # Lamp is OFF, do not turn it on or alter it
        return False, "Lamp is currently OFF (ignoring ambient signal)"

    current_dimming = st.get("dimming", 100)
    sig = signal_name.lower()

    if sig in ("blue", "help", "confirm", "input"):
        set_bulb_pilot(lamp_info, {"state": True, "r": 0, "g": 0, "b": 255, "dimming": current_dimming})
        print(f"🔵 Lamp Ambient Signal: Needs User Help/Confirmation (Blue @ {current_dimming}%)")
        return True, "blue"
    elif sig in ("red", "issue", "error", "fail"):
        set_bulb_pilot(lamp_info, {"state": True, "r": 255, "g": 0, "b": 0, "dimming": current_dimming})
        print(f"🔴 Lamp Ambient Signal: Issue Occurred (Red @ {current_dimming}%)")
        return True, "red"
    elif sig in ("green", "success", "done", "completed"):
        set_bulb_pilot(lamp_info, {"state": True, "r": 0, "g": 255, "b": 0, "dimming": current_dimming})
        print(f"🟢 Lamp Ambient Signal: Task Completed (Green for {duration}s @ {current_dimming}%)")
        # Launch non-blocking background process to revert to warm white after `duration` seconds
        cmd = [sys.executable, os.path.abspath(__file__), "--_revert_worker", str(duration), str(current_dimming)]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True, "green"
    elif sig in ("warm", "default", "reset", "normal"):
        set_bulb_pilot(lamp_info, {"state": True, "temp": 2700, "dimming": current_dimming})
        print(f"🛋️ Lamp Ambient Signal: Restored to Default Warm White (2700K @ {current_dimming}%)")
        return True, "warm"
    else:
        print(f"Unknown signal '{signal_name}'. Choices: blue, red, green, warm")
        return False, "unknown"

def run_strobe_alert(target_key, cycles=None, speed=0.22, loop=False):
    targets = resolve_target_bulbs(target_key)
    target_ips = [b_info["ip"] for _, b_info in targets]

    running = [True]
    def sig_handler(signum, frame):
        running[0] = False
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.3)

    count = 0
    try:
        while running[0]:
            p1 = json.dumps({"method": "setPilot", "params": {"state": True, "dimming": 10, "temp": 2200}}).encode()
            for ip in target_ips:
                try:
                    sock.sendto(p1, (ip, UDP_PORT))
                except Exception:
                    pass
            time.sleep(speed)
            if not running[0]:
                break

            p2 = json.dumps({"method": "setPilot", "params": {"state": True, "dimming": 100, "temp": 6500}}).encode()
            for ip in target_ips:
                try:
                    sock.sendto(p2, (ip, UDP_PORT))
                except Exception:
                    pass
            time.sleep(speed)

            count += 1
            if not loop and cycles and count >= cycles:
                break
    finally:
        sock.close()
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass

def format_all_statuses(targets=None):
    if targets is None:
        cfg = load_config()
        targets = [(k, v) for k, v in cfg.get("bulbs", {}).items()]

    lines = ["💡 WiZ Smart Bulbs Status:"]
    for b_id, b_info in targets:
        name = b_info.get("name", b_id)
        b_type = b_info.get("type", "Smart Bulb")
        ip = b_info.get("ip")
        mac = b_info.get("mac", "")
        st = get_bulb_status(ip)
        lines.append(f"\n📍 {name} [{b_type}] ({ip}):")
        if not st:
            lines.append(f"  • Status:      OFFLINE / Unreachable (MAC: {mac})")
        else:
            lines.append(f"  • Power:       {st['state']}")
            lines.append(f"  • Brightness:  {st['dimming']}%")
            if st.get("rgb"):
                lines.append(f"  • Color:       {st['rgb']}")
            lines.append(f"  • Color Temp:  {st['temp']}K" if st['temp'] != "N/A" else "  • Color Temp:  N/A")
            lines.append(f"  • Scene ID:    {st['sceneId']}")
            lines.append(f"  • Signal:      {st['rssi']} dBm")
    return "\n".join(lines)

def main():
    args_list = sys.argv[1:]
    target_override = None

    known_targets = ("yash", "lamp", "main", "myroom", "room", "nilesh", "all", "both", "tbulb", "t-bulb", "t_bulb", "ceiling")
    if len(args_list) >= 2 and args_list[0].lower() == "t" and args_list[1].lower() == "bulb":
        target_override = "tbulb"
        args_list = args_list[2:]
    elif args_list and args_list[0].lower() in known_targets:
        target_override = args_list[0].lower()
        args_list = args_list[1:]

    parser = argparse.ArgumentParser(description="Philips WiZ Smart Bulb Controller")
    parser.add_argument("-t", "--target", default=target_override, help="Target: lamp, yash, myroom, nilesh, all")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("on", help="Turn target bulb(s) ON")
    subparsers.add_parser("off", help="Turn target bulb(s) OFF")
    subparsers.add_parser("toggle", help="Toggle target bulb(s) power")
    subparsers.add_parser("status", help="Get status of target bulb(s) or all bulbs")

    p_dim = subparsers.add_parser("dim", help="Set brightness (10-100%)")
    p_dim.add_argument("level", type=int, help="Brightness percentage (10 to 100)")

    p_temp = subparsers.add_parser("temp", help="Set color temperature (2200-6500 Kelvin)")
    p_temp.add_argument("kelvin", type=int, help="Kelvin value (2200 = very warm, 6500 = cool white)")

    # Color commands (for RGB bulbs like A60 lamp)
    p_color = subparsers.add_parser("color", help="Set RGB color (r g b or name: red, green, blue, purple, etc.)")
    p_color.add_argument("color_or_r", type=str, help="Color name (red, blue, etc.) or Red value (0-255)")
    p_color.add_argument("g", type=int, nargs="?", default=None, help="Green value (0-255)")
    p_color.add_argument("b", type=int, nargs="?", default=None, help="Blue value (0-255)")

    for cname in NAMED_COLORS:
        subparsers.add_parser(cname, help=f"Set color to {cname}")

    subparsers.add_parser("warm", help="Set to warm white (~2700K)")
    subparsers.add_parser("cool", help="Set to cool white (~6500K)")
    subparsers.add_parser("neutral", help="Set to neutral white (~4000K)")
    subparsers.add_parser("reading", help="Set to Reading light (4200K, 100% brightness)")
    subparsers.add_parser("relax", help="Set to Relax mode (2700K, 60% brightness)")
    subparsers.add_parser("focus", help="Set to Focus / Study mode (5000K, 100% brightness)")
    subparsers.add_parser("cozy", help="Set to Cozy mode (Scene 6)")

    # Ambient AI Signal command
    p_sig = subparsers.add_parser("signal", help="Ambient AI status signaling on Room Lamp (blue, red, green, warm)")
    p_sig.add_argument("type", choices=["blue", "help", "confirm", "red", "error", "issue", "green", "success", "done", "warm", "default", "reset"], help="Signal type")
    p_sig.add_argument("-d", "--duration", type=int, default=10, help="Duration in seconds before green reverts to warm (default: 10s)")

    p_alert = subparsers.add_parser("alert", help="Fast High-Contrast Strobe Alert (10% Warm <-> 100% Cool)")
    p_alert.add_argument("action", nargs="?", default="burst", choices=["start", "stop", "burst", "loop"], help="start, stop, or burst")
    p_alert.add_argument("-c", "--cycles", type=int, default=6, help="Number of flash cycles (default: 6)")
    p_alert.add_argument("-s", "--speed", type=float, default=0.22, help="Speed per phase in seconds (default: 0.22)")

    p_scene = subparsers.add_parser("scene", help="Set scene by name or ID")
    p_scene.add_argument("name", type=str, help="Scene name (e.g. cozy, daylight, candlelight, relax, focus)")

    subparsers.add_parser("scan", help="Scan network for all WiZ bulbs")

    # Internal worker modes
    parser.add_argument("--_alert_worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--_cycles", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--_speed", type=float, default=0.22, help=argparse.SUPPRESS)

    parser.add_argument("--_revert_worker", nargs=2, type=int, metavar=("DURATION", "DIMMING"), help=argparse.SUPPRESS)

    args = parser.parse_args(args_list)

    if args._alert_worker:
        loop = (args._cycles == 0)
        run_strobe_alert(args.target, cycles=args._cycles, speed=args._speed, loop=loop)
        return

    if args._revert_worker:
        duration, dimming = args._revert_worker
        time.sleep(duration)
        cfg = load_config()
        lamp_info = cfg.get("bulbs", {}).get("lamp")
        if lamp_info:
            st = get_bulb_status(lamp_info["ip"])
            if st and st["state"] == "ON":
                set_bulb_pilot(lamp_info, {"state": True, "temp": 2700, "dimming": dimming})
        return

    target = args.target

    if not args.command or args.command == "status":
        if target:
            targets = resolve_target_bulbs(target)
            print(format_all_statuses(targets))
        else:
            print(format_all_statuses())
    elif args.command == "signal":
        handle_ambient_signal(args.type, duration=args.duration)
    elif args.command == "on":
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True}), "Turn ON")
    elif args.command == "off":
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": False}), "Turn OFF")
    elif args.command == "toggle":
        def toggle_b(b):
            st = get_bulb_status(b["ip"])
            if not st:
                return False, None
            new_state = False if st["state"] == "ON" else True
            return set_bulb_pilot(b, {"state": new_state})
        execute_action(target, toggle_b, "Toggle Power")
    elif args.command == "dim":
        level = max(10, min(100, args.level))
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "dimming": level}), f"Set Dimming {level}%")
    elif args.command == "temp":
        k = max(2200, min(6500, args.kelvin))
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "temp": k}), f"Set Color Temp {k}K")
    elif args.command in NAMED_COLORS:
        r, g, b = NAMED_COLORS[args.command]
        execute_action(target, lambda bl: set_bulb_pilot(bl, {"state": True, "r": r, "g": g, "b": b}), f"Set Color to {args.command.title()}")
    elif args.command == "color":
        c_in = args.color_or_r.lower()
        if c_in in NAMED_COLORS:
            r, g, b = NAMED_COLORS[c_in]
        elif args.g is not None and args.b is not None:
            r = max(0, min(255, int(c_in)))
            g = max(0, min(255, args.g))
            b = max(0, min(255, args.b))
        else:
            print(f"Unknown color '{args.color_or_r}'. Available names: {', '.join(NAMED_COLORS.keys())}")
            return
        execute_action(target, lambda bl: set_bulb_pilot(bl, {"state": True, "r": r, "g": g, "b": b}), f"Set Color to RGB({r},{g},{b})")
    elif args.command == "warm":
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "temp": 2700}), "Set Warm White (2700K)")
    elif args.command == "cool":
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "temp": 6500}), "Set Cool White (6500K)")
    elif args.command == "neutral":
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "temp": 4000}), "Set Neutral White (4000K)")
    elif args.command == "reading":
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "temp": 4200, "dimming": 100}), "Set Reading Light (4200K, 100%)")
    elif args.command == "relax":
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "temp": 2700, "dimming": 60}), "Set Relax Light (2700K, 60%)")
    elif args.command == "focus":
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "temp": 5000, "dimming": 100}), "Set Focus Light (5000K, 100%)")
    elif args.command == "cozy":
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "sceneId": 6}), "Set Cozy Mode")
    elif args.command == "alert":
        if args.action == "stop":
            stop_background_alert(quiet=False)
            execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "dimming": 100, "temp": 6500}), "Restore Daylight Cool White", stop_alert=False)
        elif args.action in ("start", "loop"):
            stop_background_alert(quiet=True)
            cmd = [sys.executable, os.path.abspath(__file__), "--_alert_worker", "--_cycles", "0", "--_speed", str(args.speed)]
            if target:
                cmd.extend(["-t", target])
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            with open(PID_FILE, "w") as f:
                f.write(str(p.pid))
            print(f"🚨 Continuous high-contrast strobe alert STARTED (PID {p.pid}).")
            print("Run 'wiz alert stop' or say 'stop alert' to cancel.")
        else:
            stop_background_alert(quiet=True)
            print(f"🚨 Running {args.cycles}-cycle fast strobe alert (10% Warm <-> 100% Cool White)...")
            run_strobe_alert(target, cycles=args.cycles, speed=args.speed, loop=False)
            print("Alert sequence finished.")
    elif args.command == "scene":
        s_id = SCENES.get(args.name.lower(), args.name)
        try:
            s_id = int(s_id)
        except ValueError:
            s_id = 14
        execute_action(target, lambda b: set_bulb_pilot(b, {"state": True, "sceneId": s_id}), f"Set Scene '{args.name}'")
    elif args.command == "scan":
        print("Scanning local subnet for all WiZ bulbs...")
        devs = scan_network()
        print(f"\nFound {len(devs)} WiZ bulb(s) on network:")
        cfg = load_config()
        known_macs = {v.get("mac"): (k, v.get("name")) for k, v in cfg.get("bulbs", {}).items()}
        for ip, d in sorted(devs.items()):
            mac = d.get("mac")
            known = known_macs.get(mac)
            label = f"[{known[1]}]" if known else "[Unassigned]"
            state = "ON" if d.get("state") else "OFF"
            print(f"  • {ip} -> {label} | MAC: {mac} | State: {state} | RSSI: {d.get('rssi')} dBm")

if __name__ == "__main__":
    main()
