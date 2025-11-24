# skills/automation.py
import re
import time
import webbrowser


def _lazy_imports():
    try:
        import pyautogui  # type: ignore
    except Exception:
        pyautogui = None
    try:
        import pyperclip  # type: ignore
    except Exception:
        pyperclip = None
    return pyautogui, pyperclip


def handle(command: str) -> str:
    cmd = command.strip()
    lower = cmd.lower()

    # Type text: "type <text>" or "write <text>"
    m = re.search(r"\b(type|write)\s+['\"]?(.+?)['\"]?$", lower)
    if m:
        text = cmd[m.start(2):m.end(2)]  # preserve original casing
        return _type_text(text)

    # Paste text: "paste <text>"
    m = re.search(r"\bpaste\s+['\"]?(.+?)['\"]?$", lower)
    if m:
        text = cmd[m.start(1):m.end(1)]
        return _paste_text(text)

    # Press keys: "press <keys>" e.g., press enter, press ctrl+s, press win+r
    m = re.search(r"\bpress\s+(.+)$", lower)
    if m:
        combo = m.group(1).strip()
        return _press_keys(combo)

    # WhatsApp message via web: "send message to <number>: <text>" or "whatsapp <number> <text>"
    m = re.search(r"\bsend\s+message\s+to\s+(\+?\d+)[\s:，,:]+(.+)$", lower)
    if not m:
        m = re.search(r"\bwhatsapp\s+(\+?\d+)\s+(.+)$", lower)
    if m:
        number = m.group(1)
        text = cmd[cmd.lower().find(m.group(2)):].strip()
        return _send_whatsapp(number, text)

    return (
        "I can type, paste, press keys, and send WhatsApp Web messages. "
        "Try: 'type Hello there', 'paste Lorem ipsum', 'press ctrl+s', "
        "or 'send message to +1234567890: Hi!'."
    )


def _type_text(text: str) -> str:
    pyautogui, _ = _lazy_imports()
    if not pyautogui:
        return "Please install pyautogui: pip install pyautogui"
    time.sleep(0.2)
    pyautogui.typewrite(text, interval=0.02)
    return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"


def _paste_text(text: str) -> str:
    pyautogui, pyperclip = _lazy_imports()
    if not pyautogui:
        return "Please install pyautogui: pip install pyautogui"
    if not pyperclip:
        return "Please install pyperclip: pip install pyperclip"
    try:
        pyperclip.copy(text)
        time.sleep(0.1)
        # ctrl+v paste
        pyautogui.hotkey('ctrl', 'v')
        return f"Pasted {len(text)} characters"
    except Exception as e:
        return f"❌ Paste failed: {e}"


def _press_keys(combo: str) -> str:
    pyautogui, _ = _lazy_imports()
    if not pyautogui:
        return "Please install pyautogui: pip install pyautogui"
    combo = combo.replace("+", " ").replace("-", " ")
    keys = [k.strip() for k in re.split(r"[\s,]+", combo) if k.strip()]
    if not keys:
        return "Specify keys to press, e.g., 'press ctrl s'"
    try:
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return f"Pressed: {'+'.join(keys)}"
    except Exception as e:
        return f"❌ Key press failed: {e}"


def _send_whatsapp(number: str, text: str) -> str:
    try:
        from urllib.parse import quote
        url = f"https://wa.me/{number}?text={quote(text)}"
        webbrowser.open(url)
        return f"Opening WhatsApp Web for {number}. After it loads, press Enter to send."
    except Exception as e:
        return f"❌ WhatsApp send failed: {e}"




