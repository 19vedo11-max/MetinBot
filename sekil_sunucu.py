"""Sekil modeli GPU sunucusu (yolo_env ile calisir). Bot kareyi paylasilan bellege yazar, sunucu YOLO cikarimi yapip
sonucu JSON olarak paylasilan bellege yazar. Tek kopya (mutex); bot PID'i oluince kendini kapatir.
Kullanim: pythonw sekil_sunucu.py <bot_pid>"""
import ctypes
import json
import os
import struct
import sys
import time
from multiprocessing import shared_memory

import numpy as np

KLASOR = os.path.dirname(os.path.abspath(__file__))
AGIRLIK = os.path.join(KLASOR, "runs", "yaratik", "weights", "best.pt")
KARE_AD, SONUC_AD = "metinbot_kare", "metinbot_sonuc"
KARE_BASLIK = 32          # <Q sayac, I h, I w, I bot_pid
KARE_BOY = KARE_BASLIK + 1200 * 2100 * 3
SONUC_BOY = 1 << 16       # <Q kare_sayac, d zaman, I uzunluk, I hazir, f ms ; sonra JSON
SONUC_BASLIK = 32
MAX_HZ = 15.0


def _pid_canli(pid):
    if not pid:
        return False
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x00100000 | 0x1000, False, int(pid))     # SYNCHRONIZE | QUERY_LIMITED
    if not h:
        return False
    r = k.WaitForSingleObject(h, 0)
    k.CloseHandle(h)
    return r == 258                                              # WAIT_TIMEOUT: hala calisiyor


def _bagla(ad, boy, bekle=60.0):
    try:
        return shared_memory.SharedMemory(name=ad, create=True, size=boy)
    except FileExistsError:
        return shared_memory.SharedMemory(name=ad)


def main():
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\metinbot_sekil_sunucu")
    if ctypes.windll.kernel32.GetLastError() == 183:
        return                                                   # zaten calisiyor
    from ultralytics import YOLO
    kare_m = _bagla(KARE_AD, KARE_BOY)
    sonuc_m = _bagla(SONUC_AD, SONUC_BOY)
    kb, sb = kare_m.buf, sonuc_m.buf
    struct.pack_into("<I", sb, 20, 0)                            # eski hazir bayragini sil

    def mtime():
        try:
            return os.path.getmtime(AGIRLIK)
        except OSError:
            return 0.0

    def yukle():
        m = YOLO(AGIRLIK)
        m.predict(np.zeros((960, 960, 3), np.uint8), imgsz=960, half=True, device=0, verbose=False)
        return m

    model = yukle()
    mt = mtime()
    adlar = model.names
    struct.pack_into("<I", sb, 20, 1)                            # hazir
    son, son_t, bos_t = 0, 0.0, time.time()
    while True:
        cur = struct.unpack_from("<I", kb, 16)[0]
        if cur and cur != pid:
            pid = cur                                            # bot yeniden basladi: yenisini izle
        if not _pid_canli(pid):
            if time.time() - bos_t > 5:
                break
        else:
            bos_t = time.time()
        if mtime() != mt:
            time.sleep(5)                                        # yazim bitsin
            try:
                model = yukle()
                adlar = model.names
            except Exception:
                pass
            mt = mtime()
        c1, h, w = struct.unpack_from("<QII", kb, 0)
        if c1 == son or not h or not w or time.time() - son_t < 1.0 / MAX_HZ:
            time.sleep(0.01)
            continue
        kare = np.frombuffer(kb, np.uint8, h * w * 3, KARE_BASLIK).reshape(h, w, 3).copy()
        if struct.unpack_from("<Q", kb, 0)[0] != c1:
            continue                                             # yazim sirasinda degisti
        son, son_t = c1, time.time()
        t0 = time.time()
        try:
            r = model.predict(np.ascontiguousarray(kare[:, :, ::-1]), imgsz=960, conf=0.25, iou=0.5, half=True,
                              device=0, verbose=False)[0]
            kut = []
            if r.boxes is not None and len(r.boxes):
                for (x0, y0, x1, y1), s, c in zip(r.boxes.xyxy.cpu().numpy().tolist(),
                                                  r.boxes.conf.cpu().numpy().tolist(),
                                                  r.boxes.cls.cpu().numpy().astype(int).tolist()):
                    kut.append([adlar.get(c, str(c)), s, x0, y0, x1, y1])
        except Exception:
            continue
        ms = (time.time() - t0) * 1000.0
        veri = json.dumps(kut).encode()[:SONUC_BOY - SONUC_BASLIK - 1]
        sb[SONUC_BASLIK:SONUC_BASLIK + len(veri)] = veri
        struct.pack_into("<QdIIf", sb, 0, c1, time.time(), len(veri), 1, ms)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
