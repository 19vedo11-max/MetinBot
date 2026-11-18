"""Ekrandaki yaziyi Windows'un yerlesik OCR'i ile okur (ocr.ps1 uzerinden)."""
import difflib
import json
import os
import subprocess
import threading

import numpy as np
from PIL import Image

KLASOR = os.path.dirname(os.path.abspath(__file__))
_TR = str.maketrans("çğıöşüâîûÇĞİÖŞÜ", "cgiosuaiucgiosu")


def sade(s):
    """Kucuk harf, Turkce harfler sadelesmis, yalniz harf/rakam/bosluk."""
    s = s.translate(_TR).lower()
    return "".join(c if c.isalnum() else " " for c in s).strip()


def benzer(yazi, anahtar, esik=0.78):
    """anahtar, yazinin icinde (yaklasik olarak) geciyor mu?"""
    a, b = sade(yazi).replace(" ", ""), sade(anahtar).replace(" ", "")
    if not a or not b:
        return False
    if b in a:
        return True
    n = len(b)
    for i in range(0, max(1, len(a) - n + 1)):
        if difflib.SequenceMatcher(None, a[i:i + n], b).ratio() >= esik:
            return True
    return False


_sunucu = {"p": None, "kilit": threading.Lock()}


def _satir_al(p, sure):
    kutu_ = []
    t = threading.Thread(target=lambda: kutu_.append(p.stdout.readline()), daemon=True)
    t.start()
    t.join(sure)
    if t.is_alive() or not kutu_ or not kutu_[0]:
        raise RuntimeError("ocr sunucusu yanit vermedi")
    return kutu_[0].decode("utf-8", "replace").strip().lstrip("\ufeff")


def _sunucu_oku(yol):
    """Surekli acik PowerShell OCR surecine yolu yollar, kelime listesini alir (~0.1 sn)."""
    with _sunucu["kilit"]:
        p = _sunucu["p"]
        try:
            if p is None or p.poll() is not None:
                p = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                      os.path.join(KLASOR, "ocr_sunucu.ps1")],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     creationflags=0x08000000)
                _sunucu["p"] = p
                if _satir_al(p, 20) != "HAZIR":
                    raise RuntimeError("ocr sunucusu acilamadi")
            p.stdin.write((yol + "\n").encode("utf-8"))
            p.stdin.flush()
            return json.loads(_satir_al(p, 8) or "[]")
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
            _sunucu["p"] = None
            raise


def oku(kare, kutu=None, olcek=3, renkli=False):
    """kare (RGB numpy) icindeki satirlari dondurur: [{"yazi", "x", "y", "x0", "y0", "x1", "y1"}, ...]
    kutu=(x0, y0, x1, y1) yalniz o bolgeyi okur. renkli=True: arazi ustundeki renkli isim etiketleri icin
    (doygun renkli pikseller siyah, gerisi beyaz yapilir)."""
    yuk, gen = kare.shape[:2]
    x0, y0, x1, y1 = kutu if kutu else (0, 0, gen, yuk)
    x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(gen, int(x1)), min(yuk, int(y1))
    parca = kare[y0:y1, x0:x1]
    if parca.size == 0:
        return []
    if renkli:
        p = parca.astype(int)
        mx, mn = p.max(axis=2), p.min(axis=2)
        parca = np.where((mx > 120) & ((mx - mn) > 80), 0, 255).astype(np.uint8)
    img = Image.fromarray(parca)
    img = img.resize((img.width * olcek, img.height * olcek), Image.BICUBIC if renkli else Image.LANCZOS)
    yol = os.path.join(KLASOR, "goruntu", "_ocr.png")
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    img.save(yol, compress_level=1)
    try:
        kelimeler = None
        try:
            kelimeler = _sunucu_oku(yol)
        except Exception as e:
            print("ocr sunucusu:", e, "- tek seferlik yola donuldu")
        c = None if kelimeler is not None else subprocess.run(
                           ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            os.path.join(KLASOR, "ocr.ps1"), "-Yol", yol],
                           capture_output=True, timeout=25, creationflags=0x08000000)
        if kelimeler is None:
            kelimeler = json.loads(c.stdout.decode("utf-8", "replace").strip() or "[]")
    except Exception as e:  # OCR calismazsa bot durmasin
        print("ocr hatasi:", e)
        return []
    satirlar, son = [], None
    for k in kelimeler:
        wx0, wy0 = x0 + k["x"] / olcek, y0 + k["y"] / olcek
        wx1, wy1 = wx0 + k["g"] / olcek, wy0 + k["h"] / olcek
        if son is not None and son["yazi"] == k["satir"] and abs(wy0 - son["y0"]) < 14 and wx0 >= son["x0"]:
            son["x1"], son["y1"] = max(son["x1"], wx1), max(son["y1"], wy1)
            son["y0"] = min(son["y0"], wy0)
        else:
            son = {"yazi": k["satir"], "x0": wx0, "y0": wy0, "x1": wx1, "y1": wy1}
            satirlar.append(son)
    for s in satirlar:
        s["x"], s["y"] = int((s["x0"] + s["x1"]) / 2), int((s["y0"] + s["y1"]) / 2)
    return satirlar

def ad_tutar(etiket, hedef, esik=0.8):
    """Canavar adi eslesmesi (OCR gurultusune ve oyunun kisaltmasina dayanikli: 'Kotu Siy. Firtina Okcusu')."""
    import itertools
    e_k = [w for w in sade(etiket).split() if not w.isdigit() and w not in ("lv", "lu", "iv")]
    h_k = sade(hedef).split()
    if not e_k or not h_k:
        return False
    # 1) kelime kelime: aynen / benzer / kisaltma (ilk 3+ harf)
    def uyar(ew, hw):
        return ew == hw or (len(ew) >= 3 and hw.startswith(ew)) or difflib.SequenceMatcher(None, ew, hw).ratio() >= esik
    fazla = [ew for ew in e_k if len(ew) > 2 and not any(uyar(ew, hw) for hw in h_k)]
    if all(any(uyar(ew, hw) for ew in e_k) for hw in h_k) and not fazla:
        return True
    # 2) bosluksuz butun: hedefin uzun kelimelerinin 3 harfe kisaltilmis varyantlari dahil
    e_b = "".join(c for c in "".join(e_k) if not c.isdigit())
    son = h_k[-1]
    kuyruk = e_b[-(len(son) + 2):]
    if difflib.SequenceMatcher(None, kuyruk, son).ratio() < 0.6:     # son kelime (or. okcusu) etiketin sonunda olmali
        return False
    bas = h_k[0]
    if difflib.SequenceMatcher(None, e_b[:len(bas) + 1], bas).ratio() < 0.6:   # ilk kelime (or. kotu) basta olmali
        return False
    en_iyi = 0.0
    secenekler = [[w] + ([w[:3]] if len(w) >= 5 else []) for w in h_k]
    for v in itertools.product(*secenekler):
        en_iyi = max(en_iyi, difflib.SequenceMatcher(None, e_b, "".join(v)).ratio())
    return en_iyi >= 0.8
