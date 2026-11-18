"""Isim etiketlerinin solundaki yesil 'Lv N' yazisindan seviye okuma."""
import glob
import os

import cv2
import numpy as np

KLASOR = os.path.dirname(os.path.abspath(__file__))
SABLON_KLASOR = os.path.join(KLASOR, "sablon", "rakam")
BOYUT = (8, 11)  # (gen, yuk)
_sablonlar = None


def yesillik(p):
    p = p.astype(int)
    return np.clip(p[..., 1] - np.maximum(p[..., 0], p[..., 2]), 0, 255).astype(np.float32)


def rakam_glifleri(kare, sol_x, y_ust, y_alt):
    """sol_x'in solundaki 'Lv N' yazisini harflere ayirir; L ve v'den sonrakileri (rakamlar) dondurur."""
    x0 = max(0, sol_x - 58)
    y = yesillik(kare[max(0, y_ust):y_alt, x0:sol_x])
    if y.size == 0:
        return []
    dolu = (y > 45).sum(axis=0) >= 1
    gruplar, bas = [], None
    for i, d in enumerate(list(dolu) + [False]):
        if d and bas is None:
            bas = i
        elif not d and bas is not None:
            gruplar.append((bas, i))
            bas = None
    gruplar = [g for g in gruplar if (y[:, g[0]:g[1]] > 45).sum() >= 5]
    if len(gruplar) < 3:
        return []
    # sondan basla: rakamlar etikete en yakin olanlar; 'v' ile rakam arasi bosluk >= 4 sutun
    rakamlar = [gruplar[-1]]
    for g in reversed(gruplar[:-1]):
        if rakamlar[0][0] - g[1] <= 3:
            rakamlar.insert(0, g)
        else:
            break
    sonuc = []
    for a, b in rakamlar:
        parca = y[:, a:b]
        satir = np.where((parca > 45).any(axis=1))[0]
        parca = parca[satir[0]:satir[-1] + 1]
        sonuc.append(cv2.resize(parca, BOYUT, interpolation=cv2.INTER_AREA))
    return sonuc


def sablon_yukle():
    global _sablonlar
    _sablonlar = []
    for yol in glob.glob(os.path.join(SABLON_KLASOR, "*.npy")):
        ad = os.path.basename(yol)
        _sablonlar.append((ad[0], np.load(yol)))
    return _sablonlar


def _benzerlik(a, b):
    a, b = a - a.mean(), b - b.mean()
    payda = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / payda) if payda > 0 else 0.0


def seviye_oku(kare, sol_x, y_ust, y_alt, esik=0.6):
    """Seviyeyi tam sayi olarak dondurur; okunamazsa None."""
    if _sablonlar is None:
        sablon_yukle()
    glifler = rakam_glifleri(kare, sol_x, y_ust, y_alt)
    if not glifler or len(glifler) > 3 or not _sablonlar:
        return None
    metin = ""
    for g in glifler:
        ad, puan = max(((ad, _benzerlik(g, s)) for ad, s in _sablonlar), key=lambda t: t[1])
        if puan < esik:
            return None
        metin += ad
    return int(metin)
