"""Sekil modeli (YOLO11n ONNX) - bota yardimci. Model/onnxruntime yoksa sessizce devre disi.
tespit(rgb) -> [(sinif_adi, skor, x0, y0, x1, y1)]  (orijinal kare koordinati)"""
import os

import cv2
import numpy as np

KLASOR = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(KLASOR, "model", "yaratik.onnx")
SINIFLAR = ["yaratik", "metin", "npc", "oyuncu", "pazar", "esya"]


class Sekil:
    def __init__(self, yol=MODEL, imgsz=960, esik=0.25, nms=0.5):
        self.ok = False
        self.saglayici = None
        self.imgsz, self.esik, self.nms = imgsz, esik, nms
        try:
            import onnxruntime as ort
            if not os.path.exists(yol):
                return
            av = ort.get_available_providers()
            for sag in (["DmlExecutionProvider", "CPUExecutionProvider"] if "DmlExecutionProvider" in av
                        else ["CPUExecutionProvider"]):
                try:
                    so = ort.SessionOptions()
                    so.intra_op_num_threads = 2          # CPU'yu bogma
                    self.oturum = ort.InferenceSession(yol, so, providers=[sag])
                    self.saglayici = sag
                    break
                except Exception:
                    continue
            if self.saglayici is None:
                return
            self.girdi = self.oturum.get_inputs()[0].name
            self.ok = True
        except Exception:
            self.ok = False

    def tespit(self, rgb, esik=None):
        if not self.ok or rgb is None:
            return []
        try:
            esik = self.esik if esik is None else esik
            h, w = rgb.shape[:2]
            o = self.imgsz / max(h, w)
            nw, nh = int(round(w * o)), int(round(h * o))
            kare = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
            tuval = np.full((self.imgsz, self.imgsz, 3), 114, np.uint8)
            px, py = (self.imgsz - nw) // 2, (self.imgsz - nh) // 2
            tuval[py:py + nh, px:px + nw] = kare
            x = tuval.astype(np.float32).transpose(2, 0, 1)[None] / 255.0     # rgb girdi
            cikti = self.oturum.run(None, {self.girdi: x})[0][0]               # [4+nc, N]
            cikti = cikti.T
            skorlar = cikti[:, 4:]
            sinif = skorlar.argmax(1)
            skor = skorlar.max(1)
            m = skor >= esik
            if not m.any():
                return []
            b, sinif, skor = cikti[m, :4], sinif[m], skor[m]
            kutular = np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2, b[:, 2], b[:, 3]], 1)
            # sinif basina NMS (sinif ofseti ile)
            idx = cv2.dnn.NMSBoxes((kutular + np.stack([sinif * 5000, sinif * 0, sinif * 0, sinif * 0], 1)).tolist(),
                                   skor.tolist(), float(esik), self.nms)
            sonuc = []
            for i in np.array(idx).flatten():
                kx, ky, kw, kh = kutular[i]
                x0 = float(np.clip((kx - px) / o, 0, w))
                y0 = float(np.clip((ky - py) / o, 0, h))
                x1 = float(np.clip((kx + kw - px) / o, 0, w))
                y1 = float(np.clip((ky + kh - py) / o, 0, h))
                s = int(sinif[i])
                sonuc.append((SINIFLAR[s] if s < len(SINIFLAR) else str(s), float(skor[i]), x0, y0, x1, y1))
            return sonuc
        except Exception:
            return []


# ---------------------------------------------------------------- GPU sunucusu istemcisi
YOLO_PYTHONW = os.path.join(KLASOR, "yolo_env", "Scripts", "pythonw.exe")
SUNUCU = os.path.join(KLASOR, "sekil_sunucu.py")
KARE_BASLIK, KARE_BOY = 32, 32 + 1200 * 2100 * 3
SONUC_BASLIK, SONUC_BOY = 32, 1 << 16


class GpuIstemci:
    """sekil_sunucu.py ile paylasilan bellekten konusur. Sunucu baslatilamazsa/hazir olmazsa ok=False kalir
    (cagiran CPU yoluna doner). Hicbir hata disari cikmaz."""

    def __init__(self, bekle=20.0):
        self.ok = False
        self.sayac = 0
        self.yazim = {}
        self.son_sonuc = 0
        try:
            import struct
            import subprocess
            import time
            from multiprocessing import shared_memory
            self._st, self._tm = struct, time
            self.kare = self._ac(shared_memory, "metinbot_kare", KARE_BOY)
            self.sonuc = self._ac(shared_memory, "metinbot_sonuc", SONUC_BOY)
            struct.pack_into("<I", self.kare.buf, 16, os.getpid())
            if not self._hazir():
                if not (os.path.exists(YOLO_PYTHONW) and os.path.exists(SUNUCU)
                        and os.path.exists(os.path.join(KLASOR, "runs", "yaratik", "weights", "best.pt"))):
                    return
                subprocess.Popen([YOLO_PYTHONW, SUNUCU, str(os.getpid())], cwd=KLASOR, close_fds=True,
                                 creationflags=0x08000000, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                t0 = time.time()
                while time.time() - t0 < bekle and not self._hazir():
                    time.sleep(0.5)
            self.ok = self._hazir()
        except Exception:
            self.ok = False

    @staticmethod
    def _ac(sm, ad, boy):
        try:
            return sm.SharedMemory(name=ad, create=True, size=boy)
        except FileExistsError:
            return sm.SharedMemory(name=ad)

    def _hazir(self):
        return self._st.unpack_from("<I", self.sonuc.buf, 20)[0] == 1

    def yaz(self, rgb):
        h, w = rgb.shape[:2]
        if h * w * 3 > KARE_BOY - KARE_BASLIK:
            return
        b = self.kare.buf
        a = np.frombuffer(b, np.uint8, h * w * 3, KARE_BASLIK)
        a[:] = np.ascontiguousarray(rgb).reshape(-1)
        self.sayac += 1
        self.yazim[self.sayac] = self._tm.time()
        if len(self.yazim) > 50:
            self.yazim.pop(min(self.yazim))
        self._st.pack_into("<QII", b, 0, self.sayac, h, w)

    def oku(self):
        """Yeni sonuc varsa (kutular, sunucu_ms, ucdan_uca_ms) dondurur, yoksa None."""
        b = self.sonuc.buf
        c, zt, n, hz, ms = self._st.unpack_from("<QdIIf", b, 0)
        if not hz or c == self.son_sonuc or c == 0:
            return None
        veri = bytes(b[SONUC_BASLIK:SONUC_BASLIK + n])
        if self._st.unpack_from("<Q", b, 0)[0] != c:
            return None
        import json
        self.son_sonuc = c
        kut = [(k[0], float(k[1]), k[2], k[3], k[4], k[5]) for k in json.loads(veri or b"[]")]
        t_yaz = self.yazim.get(c)
        return kut, float(ms), ((self._tm.time() - t_yaz) * 1000.0 if t_yaz else 0.0)
