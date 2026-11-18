"""Masaustu kisayolu: web paneli calismiyorsa arka planda baslatir, sonra kendi penceresinde (tarayici cubugu olmadan) acar."""
import os
import sys
import socket
import subprocess
import time

KLASOR = os.path.dirname(os.path.abspath(__file__))
ADRES = "http://localhost:8765"


def _pythonw():
    p = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return p if os.path.exists(p) else sys.executable


def acik_mi():
    try:
        with socket.create_connection(("127.0.0.1", 8765), timeout=0.5):
            return True
    except OSError:
        return False


if not acik_mi():
    subprocess.Popen([_pythonw(), os.path.join(KLASOR, "web_panel.py"), "--acma"], cwd=KLASOR,
                     creationflags=0x08000000)
    for _ in range(40):
        if acik_mi():
            break
        time.sleep(0.25)

edge = next((p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if os.path.exists(p)), None)
if edge:
    subprocess.Popen([edge, f"--app={ADRES}", "--window-size=1400,900"])
else:
    os.startfile(ADRES)
