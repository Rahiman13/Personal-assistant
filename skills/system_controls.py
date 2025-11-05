# skills/system_controls.py
import os
import re
import threading
import time
import platform
import subprocess
import ctypes

# Windows MCI helpers for immediate-start/stop audio (mp3/wav)
def _mci_send(cmd: str) -> None:
    try:
        ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)  # type: ignore[attr-defined]
    except Exception:
        pass

def _mci_open(alias: str, path: str) -> None:
    # Use type mpegvideo for mp3, waveaudio for wav; 'type' can be omitted to auto-detect
    _mci_send(f'open "{path}" alias {alias}')

def _mci_play_repeat(alias: str) -> None:
    _mci_send(f'play {alias} REPEAT')

def _mci_stop_close(alias: str) -> None:
    _mci_send(f'stop {alias}')
    _mci_send(f'close {alias}')

IS_WINDOWS = platform.system() == "Windows"

# Global stop event for alarm playback and player backend
_alarm_stop_event = threading.Event()
_alarm_player_backend = None  # "mci" | "winsound" | None
_alarm_player_alias = "alarmring"


def handle(command: str) -> str:
    cmd = command.lower().strip()

    # Timers: robust detection including misspellings like "timmer"
    # Examples: "set a timer for 5 minutes", "timer 10s", "set timmer for 5 secs"
    if (
        any(k in cmd for k in ["timer", "timmer", "countdown", "alarm in", "remind me in"]) or
        re.search(r"\b(set\s+tim+er|tim+er|set\s+alarm|alarm\s+in)\b", cmd) is not None
    ):
        return _handle_timer(cmd)

    # Stop alarm / stop ringing
    if any(k in cmd for k in ["stop alarm", "stop ringing", "stop timer", "silence alarm", "dismiss alarm"]):
        return _stop_alarm_now()

    # Volume controls
    if any(k in cmd for k in ["volume", "mute", "unmute", "sound", "increase volume", "decrease volume"]):
        return _handle_volume(cmd)

    # Brightness controls
    if any(k in cmd for k in ["brightness", "screen brightness", "display brightness", "increase brightness", "decrease brightness"]):
        return _handle_brightness(cmd)

    # Combined Wi‑Fi + Bluetooth intents
    if (any(k in cmd for k in ["wifi", "wi-fi", "wi fi", "wlan"]) and any(k in cmd for k in ["bluetooth", "bt"])):
        bt_msg = _handle_bluetooth(cmd)
        wifi_msg = _handle_wifi(cmd)
        return bt_msg + "\n" + wifi_msg

    # Bluetooth controls
    if any(k in cmd for k in ["bluetooth", "bt"]):
        return _handle_bluetooth(cmd)

    # Wi‑Fi controls
    if any(k in cmd for k in ["wifi", "wi-fi", "wi fi", "wlan"]):
        return _handle_wifi(cmd)

    # Power actions
    if any(k in cmd for k in ["shutdown", "power off", "turn off"]):
        return _power_action("shutdown", cmd)
    if any(k in cmd for k in ["restart", "reboot"]):
        return _power_action("restart", cmd)
    if any(k in cmd for k in ["sleep", "suspend"]):
        return _power_action("sleep", cmd)
    if any(k in cmd for k in ["lock", "lock screen"]):
        return _power_action("lock", cmd)
    if any(k in cmd for k in ["logoff", "sign out", "log out"]):
        return _power_action("logoff", cmd)

    return (
        "I can control system actions: timer, shutdown, restart, sleep, lock, logoff. "
        "Try 'set a timer for 1 minute' or 'restart now'."
    )


# ---------------------------- Timer ----------------------------

def _parse_duration_seconds(cmd: str) -> int | None:
    # Examples: 10s, 2m, 1h, 1 hour 30 minutes, 90 seconds
    patterns = [
        r"(?P<num>\d+)\s*(?P<unit>s|sec|secs|second|seconds)\b",
        r"(?P<num>\d+)\s*(?P<unit>m|min|mins|minute|minutes)\b",
        r"(?P<num>\d+)\s*(?P<unit>h|hr|hour|hours)\b",
    ]

    total = 0
    matched = False
    for pat in patterns:
        for m in re.finditer(pat, cmd):
            matched = True
            num = int(m.group("num"))
            unit = m.group("unit")[0]
            if unit == "s":
                total += num
            elif unit == "m":
                total += num * 60
            elif unit == "h":
                total += num * 3600
    if matched:
        return total

    # Support forms like "for 5 secs", "for 2 minutes"
    m = re.search(r"\bfor\s+(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)\b", cmd)
    if m:
        num = int(m.group(1))
        unit = m.group(2)[0]
        if unit == 's':
            return num
        if unit == 'm':
            return num * 60
        if unit == 'h':
            return num * 3600

    # Simple fallback: "timer 10" => seconds
    m = re.search(r"\b(\d+)\b", cmd)
    if m:
        return int(m.group(1))

    return None


def _handle_timer(cmd: str) -> str:
    seconds = _parse_duration_seconds(cmd)
    if not seconds or seconds <= 0:
        return "❌ Couldn't parse timer duration. Try 'set a timer for 5 minutes'."

    def format_mm_ss(total_seconds: int) -> str:
        m, s = divmod(max(total_seconds, 0), 60)
        return f"{m:02d}:{s:02d}"

    def timer_thread():
        remaining = seconds
        # Live countdown display (non-blocking): update once per second
        # We avoid complex cursor control; just print lines to keep it simple and robust
        print(f"\n⏳ Timer started: {format_mm_ss(remaining)} remaining")
        while remaining > 0:
            time.sleep(1)
            remaining -= 1
            # Show periodic updates every second (could be throttled if too chatty)
            print(f"⏳ Timer: {format_mm_ss(remaining)} remaining")

        # Completion: play ring sound (prefer custom file: TIMER_RING_FILE or assets/ringtone.mp3)
        def _start_esc_listener():
            # Windows-only: listen for ESC or Enter to stop alarm immediately
            if not IS_WINDOWS:
                return
            def esc_loop():
                try:
                    import msvcrt
                    while not _alarm_stop_event.is_set():
                        if msvcrt.kbhit():
                            ch = msvcrt.getch()
                            # ESC = 0x1B, Enter = '\r' (carriage return) or '\n' on some envs
                            if ch in (b"\x1b", b"\r", b"\n"):
                                _stop_alarm_now()
                                break
                        time.sleep(0.05)
                except Exception:
                    pass
            threading.Thread(target=esc_loop, daemon=True).start()

        def play_alarm_loop():
            try:
                if IS_WINDOWS:
                    import winsound, os
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    ring_path = os.getenv("TIMER_RING_FILE")
                    if not ring_path:
                        candidate = os.path.join(base_dir, 'assets', 'ringtone.mp3')
                        ring_path = candidate if os.path.exists(candidate) else None

                    # Loop alarm until stopped or for a maximum duration
                    max_seconds = 30  # ring up to 30 seconds
                    start_t = time.time()
                    _alarm_stop_event.clear()

                    if ring_path and os.path.exists(ring_path):
                        # Use Windows MCI for immediate start/stop and looping
                        global _alarm_player_backend, _alarm_player_alias
                        _alarm_player_backend = "mci"
                        _start_esc_listener()
                        _mci_open(_alarm_player_alias, ring_path)
                        _mci_play_repeat(_alarm_player_alias)
                        while not _alarm_stop_event.is_set() and (time.time() - start_t) < max_seconds:
                            time.sleep(0.1)
                        _mci_stop_close(_alarm_player_alias)
                    else:
                        # No file; use system alias beeps
                        _alarm_player_backend = "winsound"
                        _start_esc_listener()
                        while not _alarm_stop_event.is_set() and (time.time() - start_t) < max_seconds:
                            try:
                                winsound.PlaySound("SystemNotification", winsound.SND_ALIAS)
                            except Exception:
                                winsound.MessageBeep()
                            time.sleep(0.8)
                else:
                    # Best-effort bell for non-Windows
                    max_seconds = 10
                    start_t = time.time()
                    _alarm_stop_event.clear()
                    while not _alarm_stop_event.is_set() and (time.time() - start_t) < max_seconds:
                        print("\a", end="")
                        time.sleep(1.0)
            except Exception:
                pass

        print("⏰ Timer complete! (say 'stop alarm' to silence)")
        threading.Thread(target=play_alarm_loop, daemon=True).start()

    t = threading.Thread(target=timer_thread, daemon=True)
    t.start()
    return f"✅ Timer set for {seconds} seconds. Live countdown will display here; I'll ring on completion."


def _stop_alarm_now() -> str:
    _alarm_stop_event.set()
    # Attempt to stop backend immediately
    try:
        if IS_WINDOWS:
            global _alarm_player_backend, _alarm_player_alias
            if _alarm_player_backend == "mci":
                _mci_stop_close(_alarm_player_alias)
            elif _alarm_player_backend == "winsound":
                try:
                    import winsound
                    winsound.PlaySound(None, winsound.SND_PURGE)
                except Exception:
                    pass
            _alarm_player_backend = None
    except Exception:
        pass
    return "🛑 Alarm stopped."


# ------------------------- Volume Controls ------------------------
def _handle_volume(cmd: str) -> str:
    if not IS_WINDOWS:
        return "❌ Volume control is only implemented for Windows."

    # Parse specific intents
    if "mute" in cmd and "unmute" not in cmd:
        _volume_mute()
        return "🔇 Volume muted."
    if "unmute" in cmd:
        _volume_unmute()
        return "🔈 Volume unmuted."

    # Set absolute volume percentage
    import re
    m = re.search(r"(set|increase|decrease).*volume.*?(to)?\s*(\d{1,3})\s*%?", cmd)
    if m:
        try:
            pct = int(m.group(3))
            pct = max(0, min(100, pct))
            _set_volume_percent(pct)
            return f"🔊 Volume set to {pct}%."
        except Exception as e:
            return f"❌ Couldn't set volume: {e}"

    # Relative changes
    if "increase" in cmd or "up" in cmd:
        _volume_step_up(10)
        return "🔊 Volume increased."
    if "decrease" in cmd or "down" in cmd:
        _volume_step_down(10)
        return "🔉 Volume decreased."

    return "I can control volume. Try 'set volume to 60%', 'mute', or 'volume up'."


# Low-level key events for volume control (no extra deps)
def _press_vk(vk: int, repeats: int = 1):
    try:
        user32 = ctypes.windll.user32
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002
        for _ in range(max(1, repeats)):
            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception:
        pass


def _volume_step_up(steps: int = 1):
    VK_VOLUME_UP = 0xAF
    _press_vk(VK_VOLUME_UP, steps)


def _volume_step_down(steps: int = 1):
    VK_VOLUME_DOWN = 0xAE
    _press_vk(VK_VOLUME_DOWN, steps)


def _volume_mute():
    VK_VOLUME_MUTE = 0xAD
    _press_vk(VK_VOLUME_MUTE, 1)


def _volume_unmute():
    # Toggle mute off by sending MUTE followed by a small UP
    _volume_mute()
    _volume_step_up(1)


def _set_volume_percent(pct: int):
    # Approximation: normalize to 0 first, then raise to target
    # Assume ~50 discrete steps maps to 0-100%
    total_steps = 50
    _volume_step_down(total_steps)
    up_steps = int(round((pct / 100.0) * total_steps))
    if up_steps > 0:
        _volume_step_up(up_steps)


# ----------------------- Brightness Controls ----------------------
def _handle_brightness(cmd: str) -> str:
    if not IS_WINDOWS:
        return "❌ Brightness control is only implemented for Windows."

    import re
    # Absolute set
    m = re.search(r"(set|increase|decrease).*brightness.*?(to)?\s*(\d{1,3})\s*%?", cmd)
    if m:
        try:
            pct = int(m.group(3))
            pct = max(0, min(100, pct))
            ok, err = _set_brightness_percent(pct)
            return "🔆 Brightness set to {0}%".format(pct) if ok else f"❌ Couldn't set brightness: {err or 'unknown error'}"
        except Exception as e:
            return f"❌ Couldn't set brightness: {e}"

    # Relative
    if "increase" in cmd or "up" in cmd:
        cur = _get_brightness_percent()
        if cur is None:
            return "❌ Couldn't read current brightness."
        target = min(100, cur + 10)
        ok, err = _set_brightness_percent(target)
        return "🔆 Brightness increased to {0}%".format(target) if ok else f"❌ Couldn't set brightness: {err or 'unknown error'}"
    if "decrease" in cmd or "down" in cmd:
        cur = _get_brightness_percent()
        if cur is None:
            return "❌ Couldn't read current brightness."
        target = max(0, cur - 10)
        ok, err = _set_brightness_percent(target)
        return "🔅 Brightness decreased to {0}%".format(target) if ok else f"❌ Couldn't set brightness: {err or 'unknown error'}"

    # Query
    cur = _get_brightness_percent()
    if cur is None:
        return "❌ Couldn't read current brightness."
    return f"🔆 Current brightness: {cur}%"


def _ps(cmd: str, timeout_sec: int = 5) -> subprocess.CompletedProcess:
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True, text=True, timeout=timeout_sec)


def _run_elevated_ps(cmd: str) -> tuple[bool, str | None]:
    """Trigger an elevated PowerShell to run cmd via UAC prompt. Returns immediately."""
    try:
        # Escape embedded quotes for inclusion in a double-quoted string
        ps_arg = cmd.replace('"', '`"')
        elevate = (
            "Start-Process PowerShell -Verb RunAs "
            "-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command',\"" + ps_arg + "\""
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", elevate],
            capture_output=True, text=True, timeout=5
        )
        return True, None
    except Exception as e:
        return False, str(e)


def _get_brightness_percent() -> int | None:
    try:
        ps = "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
        res = _ps(ps)
        if res.returncode == 0 and res.stdout.strip():
            val = int(''.join([c for c in res.stdout if c.isdigit()]))
            if 0 <= val <= 100:
                return val
    except Exception:
        pass
    return None


def _set_brightness_percent(pct: int) -> tuple[bool, str | None]:
    try:
        # Use WmiMonitorBrightnessMethods to set brightness
        ps = f"$b=(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods); if($b){{$b.WmiSetBrightness(1,{pct}) | Out-Null; exit 0}} else { '{exit 1}' }"
        res = _ps(ps)
        if res.returncode == 0:
            return True, None
        return False, res.stderr.strip() or res.stdout.strip()
    except Exception as e:
        return False, str(e)


# ----------------------- Bluetooth Controls ----------------------
def _handle_bluetooth(cmd: str) -> str:
    if not IS_WINDOWS:
        return "❌ Bluetooth control is only implemented for Windows."

    # Open Bluetooth settings
    if any(k in cmd for k in ["settings", "open", "pair", "add device", "devices"]):
        try:
            os.system("start ms-settings:bluetooth")
            return "🟦 Opening Bluetooth settings"
        except Exception as e:
            return f"❌ Couldn't open Bluetooth settings: {e}"

    # Direct toggle via PowerShell PnP device control (requires admin)
    if "on" in cmd or "enable" in cmd:
        ok, msg = _bluetooth_toggle(True)
        if ok:
            return "🟦 Bluetooth turned ON"
        # Fallback: open settings when toggle cannot be automated
        try:
            os.system("start ms-settings:bluetooth")
        except Exception:
            pass
        return f"❌ Couldn't turn on Bluetooth automatically: {msg or 'open settings to toggle manually'}"
    if "off" in cmd or "disable" in cmd:
        ok, msg = _bluetooth_toggle(False)
        if ok:
            return "🟦 Bluetooth turned OFF"
        try:
            os.system("start ms-settings:bluetooth")
        except Exception:
            pass
        return f"❌ Couldn't turn off Bluetooth automatically: {msg or 'open settings to toggle manually'}"

    return "I can open Bluetooth settings. Try 'open bluetooth settings' or 'bluetooth on/off'."


def _bluetooth_toggle(turn_on: bool) -> tuple[bool, str | None]:
    try:
        # Require admin for direct device enable/disable
        try:
            if IS_WINDOWS and hasattr(ctypes, 'windll') and not ctypes.windll.shell32.IsUserAnAdmin():  # type: ignore[attr-defined]
                # Request elevation prompt and run the same command elevated
                action = 'Enable-PnpDevice' if turn_on else 'Disable-PnpDevice'
                elev_cmd = (
                    "$devs = Get-PnpDevice -Class Bluetooth -Status Unknown,Error,Degraded,OK;"
                    "if($devs){ foreach($d in $devs){ try{ " + action + " -InstanceId $d.InstanceId -Confirm:$false -ErrorAction Stop }catch{} } }"
                )
                ok, err = _run_elevated_ps(elev_cmd)
                if ok:
                    return False, "Elevation requested. Approve the UAC prompt to toggle Bluetooth."
                return False, err or "Administrator privileges required to toggle Bluetooth devices."
        except Exception:
            pass
        # Find Bluetooth Radio devices and enable/disable them.
        # Requires admin privileges. We use Get-PnpDevice and Enable/Disable-PnpDevice.
        action = 'Enable-PnpDevice' if turn_on else 'Disable-PnpDevice'
        ps = (
            "$devs = Get-PnpDevice -Class Bluetooth -Status Unknown,Error,Degraded,OK;"
            "if($devs){"
            f"  foreach($d in $devs){{ try{{ {action} -InstanceId $d.InstanceId -Confirm:$false -ErrorAction Stop }}catch{{}} }}; exit 0"
            "} else { exit 1 }"
        )
        res = _ps(ps, timeout_sec=20)
        if res.returncode == 0:
            return True, None
        # Try radios via Devcon (if available)
        devcon_paths = [
            r"C:\\Windows\\System32\\devcon.exe",
            r"C:\\Windows\\SysWOW64\\devcon.exe",
        ]
        for p in devcon_paths:
            if os.path.exists(p):
                # devcon classes may differ; try enabling/disabling *BTH* devices
                cmd = f'"{p}" {("enable" if turn_on else "disable")} *BTH*'
                res2 = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8)
                if res2.returncode == 0:
                    return True, None
        return False, (res.stderr.strip() or res.stdout.strip() or "Admin rights required or device not found")
    except Exception as e:
        return False, str(e)


def _handle_wifi(cmd: str) -> str:
    if not IS_WINDOWS:
        return "❌ Wi‑Fi control is only implemented for Windows."

    # Detect Wi‑Fi interface name via netsh
    iface = _wifi_interface_name()
    if not iface:
        return "❌ Couldn't detect Wi‑Fi interface."

    # Revoke/undo previous OFF action → turn Wi‑Fi ON
    if any(k in cmd for k in ["revoke", "undo", "reverse", "revert", "restore"]):
        if ("off" in cmd) or ("disable" in cmd) or ("turned off" in cmd):
            ok, msg = _wifi_set_enabled(iface, True)
            if ok:
                return "📶 Wi‑Fi turned ON (previous OFF action reversed)"
            try:
                os.system("start ms-settings:network-wifi")
            except Exception:
                pass
            return f"❌ Couldn't re-enable Wi‑Fi automatically: {msg or 'opened settings to toggle manually'}"

    # List/scan Wi‑Fi networks
    if any(k in cmd for k in ["list", "scan", "show"]) and any(k in cmd for k in ["network", "networks", "wifi", "wi-fi", "wi fi", "wlan", "available", "devices"]):
        _wifi_enable_autoconfig(iface)
        nets = _wifi_scan_networks()
        if nets:
            preview = "\n".join([f"• {n}" for n in nets[:15]])
            more = "\n… (use 'open wifi settings' to see more)" if len(nets) > 15 else ""
            return f"📡 Available Wi‑Fi networks (top {min(15, len(nets))}):\n{preview}{more}"
        try:
            os.system("start ms-settings:network-wifi")
        except Exception:
            pass
        return "❌ Couldn't list networks. Opened Wi‑Fi settings as fallback."

    # Connect to specific SSID
    if "connect" in cmd:
        ssid = _extract_ssid(cmd)
        if not ssid:
            return "❌ Specify a network name. Example: 'connect to \"My WiFi\"'"
        _wifi_enable_autoconfig(iface)
        ok, msg = _wifi_connect_known(ssid)
        if ok:
            return f"✅ Connecting to '{ssid}'"
        try:
            os.system("start ms-settings:network-wifi")
        except Exception:
            pass
        hint = " Add the network in Settings if it isn't saved yet."
        return f"❌ Couldn't connect to '{ssid}': {msg or 'profile not found or access denied.'}{hint}"

    # Open Wi‑Fi settings explicitly
    if any(k in cmd for k in ["settings", "open", "network", "adapter"]):
        try:
            os.system("start ms-settings:network-wifi")
            return "📶 Opening Wi‑Fi settings"
        except Exception as e:
            return f"❌ Couldn't open Wi‑Fi settings: {e}"

    if "on" in cmd or "enable" in cmd:
        ok, msg = _wifi_set_enabled(iface, True)
        if ok:
            return "📶 Wi‑Fi turned ON"
        try:
            os.system("start ms-settings:network-wifi")
        except Exception:
            pass
        return f"❌ Couldn't turn on Wi‑Fi automatically: {msg or 'open settings to toggle manually'}"
    if "off" in cmd or "disable" in cmd:
        ok, msg = _wifi_set_enabled(iface, False)
        if ok:
            return "📴 Wi‑Fi turned OFF"
        try:
            os.system("start ms-settings:network-wifi")
        except Exception:
            pass
        return f"❌ Couldn't turn off Wi‑Fi automatically: {msg or 'open settings to toggle manually'}"
    if any(k in cmd for k in ["status", "state"]):
        st = _wifi_status()
        return f"📡 Wi‑Fi status: {st}" if st else "❌ Couldn't read Wi‑Fi status."

    return "I can control Wi‑Fi. Try 'wifi on', 'wifi off', or 'wifi status'."


def _wifi_interface_name() -> str | None:
    try:
        res = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "Name" in line and ":" in line:
                    name = line.split(":", 1)[1].strip()
                    if name:
                        return name
    except Exception:
        pass
    return None


def _wifi_set_enabled(iface: str, enable: bool) -> tuple[bool, str | None]:
    """
    Prefer turning Wi‑Fi radio/AutoConfig on/off without disabling the interface.
    Implementation:
      - wifi off: netsh wlan disconnect; netsh wlan set autoconfig enabled=no interface=<iface>
      - wifi on:  netsh wlan set autoconfig enabled=yes interface=<iface>
    Fallback:
      - If autoconfig commands fail, we do NOT disable the interface anymore. We return an error instead.
    """
    try:
        if enable:
            # Enable WLAN AutoConfig for the interface
            res = subprocess.run(["netsh", "wlan", "set", "autoconfig", "enabled=yes", f"interface={iface}"], capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                return True, None
            # Try elevated autoconfig as fallback
            cmd = f"netsh wlan set autoconfig enabled=yes interface='{iface}'"
            ok, err = _run_elevated_ps(cmd)
            if ok:
                return False, "Elevation requested. Approve the UAC prompt to turn Wi‑Fi ON."
            return False, err or (res.stderr.strip() or res.stdout.strip())
        else:
            # Disconnect current connection (non-destructive)
            subprocess.run(["netsh", "wlan", "disconnect"], capture_output=True, text=True, timeout=5)
            # Disable WLAN AutoConfig so Wi‑Fi behaves as off without disabling adapter
            res = subprocess.run(["netsh", "wlan", "set", "autoconfig", "enabled=no", f"interface={iface}"], capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                return True, None
            # Try elevated as fallback
            cmd = f"netsh wlan set autoconfig enabled=no interface='{iface}'"
            ok, err = _run_elevated_ps(cmd)
            if ok:
                return False, "Elevation requested. Approve the UAC prompt to turn Wi‑Fi OFF."
            return False, err or (res.stderr.strip() or res.stdout.strip())
    except Exception as e:
        return False, str(e)


def _wifi_status() -> str | None:
    try:
        res = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def _wifi_enable_autoconfig(iface: str) -> None:
    try:
        subprocess.run(["netsh", "wlan", "set", "autoconfig", "enabled=yes", f"interface={iface}"], capture_output=True, text=True, timeout=5)
    except Exception:
        pass


def _wifi_scan_networks() -> list[str]:
    try:
        res = subprocess.run(["netsh", "wlan", "show", "networks"], capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            return []
        ssids: list[str] = []
        current = None
        for raw in res.stdout.splitlines():
            line = raw.strip()
            if line.lower().startswith("ssid ") and ":" in line:
                parts = line.split(":", 1)
                name = parts[1].strip()
                if name and name not in ssids:
                    ssids.append(name)
        return ssids
    except Exception:
        return []


def _wifi_connect_known(ssid: str) -> tuple[bool, str | None]:
    try:
        # Try direct connect using existing profile
        res = subprocess.run(["netsh", "wlan", "connect", f"name={ssid}"], capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return True, None
        # Some systems require profile or explicit ssid parameter
        res2 = subprocess.run(["netsh", "wlan", "connect", f"ssid={ssid}", f"name={ssid}"], capture_output=True, text=True, timeout=10)
        if res2.returncode == 0:
            return True, None
        # If still failing, likely no saved profile exists
        return False, (res.stderr.strip() or res.stdout.strip() or res2.stderr.strip() or res2.stdout.strip())
    except Exception as e:
        return False, str(e)


# Public helpers for other modules (e.g., main loop handling Enter)
def stop_alarm_now() -> str:
    return _stop_alarm_now()

def is_alarm_active() -> bool:
    try:
        return (_alarm_player_backend is not None) and (not _alarm_stop_event.is_set())
    except Exception:
        return False


# ------------------------- Power Actions ------------------------

def _confirm_dangerous(cmd: str) -> bool:
    # Allow forced variants without confirmation: "restart now", "shutdown now"
    return any(k in cmd for k in [" now", " /f", "-f", " --force"])  # naive but useful


def _power_action(action: str, cmd: str) -> str:
    if not IS_WINDOWS:
        return "❌ System power actions are only implemented for Windows in this assistant."

    # Safety: require confirmation unless forced
    if not _confirm_dangerous(cmd):
        return (
            f"⚠️ This will {action} your computer. If you're sure, say '{action} now' to proceed."
        )

    try:
        if action == "shutdown":
            # Immediate forced shutdown
            subprocess.run(["shutdown", "/s", "/t", "0", "/f"], check=False)
            return "🛑 Shutting down..."
        if action == "restart":
            subprocess.run(["shutdown", "/r", "/t", "0", "/f"], check=False)
            return "🔄 Restarting..."
        if action == "sleep":
            # Requires hibernation enabled on some systems
            # Using rundll32 to suspend
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"], check=False)
            return "😴 Going to sleep..."
        if action == "lock":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
            return "🔒 Locking workstation..."
        if action == "logoff":
            subprocess.run(["shutdown", "/l"], check=False)
            return "🚪 Logging off..."
        return "❌ Unknown power action."
    except Exception as e:
        return f"❌ Error performing {action}: {e}"
