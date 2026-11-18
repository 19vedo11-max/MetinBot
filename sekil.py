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
