# Minimal aifc shim for Python 3.13 environments where stdlib aifc is absent.
# SpeechRecognition imports aifc at module import time for AIFF support.
# We don't use AIFF in this app (microphone input via PyAudio), so a stub is sufficient.

class Error(Exception):
    pass

def open(*args, **kwargs):  # type: ignore[override]
    raise Error("aifc module is unavailable in this environment")


