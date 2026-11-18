"""YOLO egitimi surerken bellek bekcisi: bos RAM esigin altina 3 olcum ust uste inerse botu kapatir
(komut.json 'kapat'), egitim devam eder. Egitim sureci bitince kendisi de cikar.

pythonw bellek_bekci.py <egitim_pid> [esik_mb=1200]"""
import ctypes
import os
import sys
import time

import kumanda

KLASOR = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(KLASOR, "bellek_bekci.log")


class MS(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def bos_mb():
    m = MS()
    m.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys // (1024 * 1024)


def yasiyor(pid):
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    kod = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(kod))
    ctypes.windll.kernel32.CloseHandle(h)
    return kod.value == 259


def yaz(s):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S  ") + s + "\n")


def main():
    pid = int(sys.argv[1])
    esik = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
    yaz(f"bekci basladi: egitim pid {pid}, esik {esik} MB, simdi bos {bos_mb()} MB")
    alt = 0
    while yasiyor(pid):
        b = bos_mb()
        alt = alt + 1 if b < esik else 0
        if alt >= 3:
            if kumanda.canli().get("ayakta"):
                kumanda.komut("kapat")
                yaz(f"bos RAM {b} MB < {esik} MB (3 olcum) - bot kapatildi, egitim devam ediyor")
            break
        time.sleep(10)
    yaz(f"bekci bitti (bos {bos_mb()} MB)")


if __name__ == "__main__":
    main()
