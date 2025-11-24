import threading
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import List
try:
    # For printing to terminal similarly to CLI flow
    from interface.cli_interface import show_output as _show_output, show_error as _show_error, show_success as _show_success
except Exception:
    def _show_output(msg: str) -> None:
        try:
            print("\n" + "="*60)
            print("🤖 Assistant:")
            print("-" * 20)
            print(f"   {msg}")
            print("="*60)
        except Exception:
            pass
    def _show_error(msg: str) -> None:
        try:
            print("\n❌" + "="*58)
            print("🚨 ERROR:")
            print("-" * 10)
            print(f"   {msg}")
            print("❌" + "="*58)
        except Exception:
            pass
    def _show_success(msg: str) -> None:
        try:
            print("\n✅" + "="*58)
            print("🎉 SUCCESS:")
            print("-" * 10)
            print(f"   {msg}")
            print("✅" + "="*58)
        except Exception:
            pass
try:
    # Import lazily to avoid hard failures if core isn't ready at import time
    from core.brain import process_command_with_learning as _process_command
except Exception:
    try:
        # Fallback to regular process_command if learning not available
        from core.brain import process_command as _process_command
    except Exception:
        _process_command = None  # Fallback; handler will guard

_clients_lock = threading.Lock()
_clients: List["SSEHandler"] = []
_server_thread: threading.Thread | None = None


class QuietHTTPServer(HTTPServer):
    # Suppress noisy client disconnect stack traces (e.g., WinError 10053, BrokenPipe)
    def handle_error(self, request, client_address):  # type: ignore[override]
        try:
            import sys
            exc_type, exc, _tb = sys.exc_info()
            msg = str(exc) if exc else ""
            # Ignore common transient socket disconnects
            if msg and any(k in msg for k in [
                "WinError 10053", "BrokenPipeError", "ConnectionResetError", "ConnectionAbortedError"
            ]):
                return
        except Exception:
            pass
        # Fallback to default behavior
        try:
            super().handle_error(request, client_address)
        except Exception:
            pass


class SSEHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        # Quiet server logs
        return

    def end_headers(self) -> None:
        # Allow CORS for local file usage
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*, Content-Type, Authorization, Accept, Origin, Cache-Control, X-Requested-With")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_OPTIONS(self):
        # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*, Content-Type, Authorization, Accept, Origin, Cache-Control, X-Requested-With")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/events"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "keep-alive")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            # Register client
            with _clients_lock:
                _clients.append(self)
            try:
                # Keep connection open
                while True:
                    time.sleep(60)
                    # Send keepalive comment
                    try:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                    except Exception:
                        break
            finally:
                with _clients_lock:
                    if self in _clients:
                        _clients.remove(self)
        elif self.path.startswith("/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{\"ok\": true}")
        elif self.path == "/" or self.path.startswith("/ui"):
            # Serve the UI HTML to avoid file:// CORS issues
            try:
                import os
                from pathlib import Path
                ui_path = Path(__file__).resolve().parent / "ui.html"
                if not ui_path.exists():
                    raise FileNotFoundError(str(ui_path))
                content = ui_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self.send_response(500)
                self.end_headers()
        elif self.path.startswith("/file.js"):
            # Serve the main UI script
            try:
                from pathlib import Path
                js_path = (Path(__file__).resolve().parents[1]) / "file.js"
                content = js_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/command"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length > 0 else b"{}"
                data = json.loads(body.decode("utf-8") or "{}")
            except Exception:
                data = {}

            text = str(data.get("text") or "").strip()
            if not text:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{\"error\": \"Missing text\"}")
                return

            # Echo user's web command to terminal for parity with CLI
            try:
                print(f"🧑 You (web): {text}")
            except Exception:
                pass

            # Emit UI events around processing
            try:
                emit_heard(text)
                emit_processing()
            except Exception:
                pass

            # Process the command via core.brain
            response_text = ""
            try:
                if _process_command is None:
                    response_text = "⚠️ Command processor not available. Please restart the application."
                else:
                    response_text = _process_command(text)
                    # Ensure we always have a response
                    if not response_text or not response_text.strip():
                        response_text = "Command processed successfully."
            except Exception as e:
                response_text = f"❌ Error: {str(e)}"
                import traceback
                traceback.print_exc()

            # Speak event for UI and finish with listening
            try:
                emit_speaking(response_text)
                emit_listening()
            except Exception:
                pass

            # Print structured response to terminal similar to CLI
            try:
                lower = (response_text or "").lower()
                if ("✅" in response_text) or ("success" in lower):
                    _show_success(response_text)
                elif ("❌" in response_text) or ("error" in lower):
                    _show_error(response_text)
                else:
                    _show_output(response_text)
            except Exception:
                pass

            # Respond JSON
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            out = json.dumps({"response": response_text}).encode("utf-8")
            try:
                self.wfile.write(out)
            except Exception:
                pass
            return

        self.send_response(404)
        self.end_headers()


def _broadcast(event: str, payload: dict) -> None:
    data = json.dumps({"type": event, **payload})
    msg = f"event: {event}\ndata: {data}\n\n".encode("utf-8")
    to_remove: List[SSEHandler] = []
    with _clients_lock:
        for client in list(_clients):
            try:
                client.wfile.write(msg)
                client.wfile.flush()
            except Exception:
                to_remove.append(client)
        for c in to_remove:
            if c in _clients:
                _clients.remove(c)


def emit_heard(text: str) -> None:
    _broadcast("heard", {"text": text})


def emit_processing() -> None:
    _broadcast("processing", {})


def emit_speaking(text: str) -> None:
    _broadcast("speaking", {"text": text})


def emit_listening() -> None:
    _broadcast("listening", {})


def emit_log(message: str) -> None:
    # Lightweight log event for UI console
    _broadcast("log", {"message": message})


def start_server(host: str = "127.0.0.1", port: int = 8008) -> None:
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        return

    def _run():
        httpd = QuietHTTPServer((host, port), SSEHandler)
        try:
            httpd.serve_forever()
        except Exception:
            pass

    _server_thread = threading.Thread(target=_run, daemon=True)
    _server_thread.start()


