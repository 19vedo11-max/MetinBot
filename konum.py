"""Karakterin harita konumu (mini haritadan) + kalici engel hafizasi. bot.py'den bagimsiz, yalniz cv2/numpy.

YONTEM
  Mini harita (sag ust, YUVARLAK, kuzey hep yukari - DONMEZ; yalniz ok simgesi ve gorus konisi doner) ayni
  dokuyu gosteren bir goruntu: kayitli harita ile ayni cizim. Kirpinti orta karesi (ok, kirmizi/sari/yesil/gri
  noktalar boyanarak silinir) kayitli haritada sablon eslemeyle (3 kanal: gri, B-R, G-(R+B)/2) aranir.
  Iki kademe:
   1) INCE : Bakra_buyuk.png (599x524), olcek 1.0 (mini piksel = buyuk harita pikseli; plaza uzerinde olculdu,
             0.8-1.1 araliginda tepe 1.0'da). Buyuk harita Bakra'nin yalniz orta kismini kapsar.
   2) KABA : Bakra.png (316x318, tum harita), olcek 0.25 (buyuk harita Bakra'ya 0.25 ile oturur, skor 0.71).
             Cozunurluk dusuk (mini 80 px -> 20 px): belirsizlik buyuk, tahmin +-10 Bakra pikseli.
  DONEN x, y HER ZAMAN Bakra (316x318) oranidir (harita="Bakra"), ince kademe sonucu da oraya cevrilir:
     bakra_px = BUYUK_BOLGE[:2] + buyuk_px * 0.25. harita="Bakra_buyuk" istenirse yalniz ince kademe, buyuk oran.
  onceki=(x, y) verilirse (Bakra orani) arama o noktanin etrafinda daralir (hiz + tutarlilik); pencerede skor
  dusukse genel aramaya doner.
"""
import json
import math
import os
import threading
import time

import cv2
import numpy as np

KLASOR = os.path.dirname(os.path.abspath(__file__))
HARITA_KLASOR = os.path.join(KLASOR, "goruntu", "haritalar")

# --- sabitler (2026-11-19 olculdu; 1920x1171 / 1920x1111 karelerde ayni, mini harita sag-ust capali) ---
MINI_MERKEZ_SAGDAN = 84      # mini harita merkezi: kare_genislik - 84
MINI_MERKEZ_Y = 86
MINI_YARI = 44               # sablon yarim kenari (yuvarlak ic yaricap ~54'e sigan kare)
OLCEK_BUYUK = 1.0            # mini px -> Bakra_buyuk px
OLCEK_BAKRA = 0.25           # mini px -> Bakra px
BUYUK_BOLGE = (86.0, 105.0)  # Bakra_buyuk'un Bakra pikselindeki sol-ust kosesi (boyut 150x131 Bakra px)
BUYUK_BAKRA_OLCEK = 0.25
AGIRLIK = (1.0, 1.0, 0.5)
ESIK_INCE = 0.50             # ince kademe kabul skoru
ESIK_KABA = 0.65             # kaba kademe kabul skoru
ESIK_KABA_PENCERE = 0.50     # onceki konum penceresi icinde kaba esik
PENCERE_BAKRA_PX = 28        # onceki konum yaricapi (Bakra px; ~ mini haritanin yarisi)

_C = {}


def _kaldir_isaret(g, buyuk):
    b, gg, r = [g[..., i].astype(int) for i in range(3)]
    if buyuk:   # etiket yazisi (beyaz), yesil/sari isaret kareleri, ust bar, olcek, sag dugmeler
        m = ((r > 185) & (gg > 185) & (b > 185)) | ((gg > 170) & (r < 130) & (b < 130)) | ((r > 170) & (gg > 170) & (b < 110))
        m = m.astype(np.uint8)
        m[0:30, 0:312] = 1
        m[488:524, 0:80] = 1
        m[0:110, 540:599] = 1
        m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    else:
        m = (((gg > 170) & (r < 140) & (b < 140)) | ((b > 200) & (gg > 180) & (r < 150)) | ((r > 170) & (gg > 170) & (b < 110))).astype(np.uint8)
        m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    return cv2.inpaint(g, m, 3, cv2.INPAINT_TELEA)


def _ozellik(img, sg):
    f = img.astype(np.float32)
    b, g, r = cv2.split(f)
    return [cv2.GaussianBlur(c, (0, 0), sg) for c in ((b + g + r) / 3, b - r, g - (r + b) / 2)]


def _yukle():
    if _C:
        return _C
    for ad, buyuk, sg, ek in (("Bakra_buyuk", True, 0.8, 0.5), ("Bakra", False, 0.8, 1.0)):   # ek: hiz icin ince kademe yarim cozunurlukte
        im = cv2.imread(os.path.join(HARITA_KLASOR, ad + ".png"))
        if im is None:
            continue
        W0, H0 = im.shape[1], im.shape[0]
        im = _kaldir_isaret(im, buyuk)
        if ek != 1.0:
            im = cv2.resize(im, None, fx=ek, fy=ek, interpolation=cv2.INTER_AREA)
        _C[ad] = (_ozellik(im, sg), W0, H0, sg, ek)
    return _C


def _mini(kare):
    """Mini harita ortasindan kare sablon (BGR) ya da None. Noktalar/ok boyanip silinir."""
    h, w = kare.shape[:2]
    cx, cy = w - MINI_MERKEZ_SAGDAN, MINI_MERKEZ_Y
    if cx - 56 < 0 or cy - 56 < 0 or cy + 56 > h:
        return None
    m = kare[cy - 56:cy + 56, cx - 56:cx + 56].copy()
    b, g, r = [m[..., i].astype(int) for i in range(3)]
    bad = ((r > 140) & (g < 90)) | ((r > 170) & (g > 140) & (b < 130)) | ((g > 150) & (r < 150) & (b < 120)) | ((r > 150) & (g > 150) & (b > 150))
    bad = cv2.dilate(bad.astype(np.uint8), np.ones((3, 3), np.uint8))
    bad[56 - 9:56 + 9, 56 - 9:56 + 9] = 1        # karakter oku
    m = cv2.inpaint(m, bad, 3, cv2.INPAINT_TELEA)
    return m[56 - MINI_YARI:56 + MINI_YARI, 56 - MINI_YARI:56 + MINI_YARI]


def _esle(ad, mini, olcek, pencere=None):
    """-> (skor, x_px, y_px, ikinci_tepe_skoru) harita pikselinde (merkez), ya da None. pencere=(cx,cy,yaricap) harita px."""
    ozl, W, H, sg, ek = _yukle()[ad]
    olcek = olcek * ek
    W, H = W * ek, H * ek
    if pencere is not None:
        pencere = tuple(v * ek for v in pencere)
    d = int(round(mini.shape[0] * olcek))
    if d < 12:
        return None
    t = cv2.resize(mini, (d, d), interpolation=cv2.INTER_AREA)
    tf = _ozellik(t, sg)
    x0 = y0 = 0
    harita = ozl
    if pencere is not None:
        cx, cy, ry = pencere
        x0, y0 = int(max(0, cx - ry - d / 2)), int(max(0, cy - ry - d / 2))
        x1, y1 = int(min(W, cx + ry + d / 2)), int(min(H, cy + ry + d / 2))
        if x1 - x0 < d + 2 or y1 - y0 < d + 2:
            return None
        harita = [c[y0:y1, x0:x1] for c in ozl]
    tot = 0
    for hc, tc, w in zip(harita, tf, AGIRLIK):
        tot = tot + w * cv2.matchTemplate(hc, tc, cv2.TM_CCOEFF_NORMED)
    tot = np.nan_to_num(tot / sum(AGIRLIK), nan=-1.0, posinf=-1.0, neginf=-1.0)
    _, mx, _, loc = cv2.minMaxLoc(tot)
    t2 = tot.copy()
    r = max(4, int(d / 3))
    t2[max(0, loc[1] - r):loc[1] + r + 1, max(0, loc[0] - r):loc[0] + r + 1] = -1
    return mx, (loc[0] + d / 2 + x0) / ek, (loc[1] + d / 2 + y0) / ek, float(t2.max())


def _guven(skor, ikinci, esik):
    a = max(0.0, min(1.0, (skor - esik + 0.15) / 0.4))
    marj = max(0.0, min(1.0, 0.4 + (skor - ikinci) / 0.08 * 0.6))
    return round(a * marj, 3)


def harita_konumu(kare, harita="Bakra", onceki=None):
    """Kareden (BGR, tam ekran) karakterin harita konumu: {"x","y","guven","skor","kaynak"} ya da None.
    harita="Bakra": x,y Bakra(316x318) orani. harita="Bakra_buyuk": x,y buyuk harita orani (yalniz ince kademe).
    onceki: (x, y) ayni harita oraninda onceki konum."""
    try:
        c = _yukle()
        mini = _mini(kare)
        if mini is None or "Bakra_buyuk" not in c and "Bakra" not in c:
            return None
        bw, bh = c["Bakra_buyuk"][1:3] if "Bakra_buyuk" in c else (599, 524)
        kw, kh = c["Bakra"][1:3] if "Bakra" in c else (316, 318)
        s = BUYUK_BAKRA_OLCEK
        ince_pen = kaba_pen = None
        if onceki is not None:
            ox, oy = onceki
            if harita == "Bakra":
                bx, by = ox * kw, oy * kh
                kaba_pen = (bx, by, PENCERE_BAKRA_PX)
                ince_pen = ((bx - BUYUK_BOLGE[0]) / s, (by - BUYUK_BOLGE[1]) / s, PENCERE_BAKRA_PX / s)
            else:
                ince_pen = (ox * bw, oy * bh, PENCERE_BAKRA_PX / s)
        sonuc = None
        # 1) ince
        if "Bakra_buyuk" in c:
            r = _esle("Bakra_buyuk", mini, OLCEK_BUYUK, ince_pen)
            if r is None and ince_pen is not None:
                r = _esle("Bakra_buyuk", mini, OLCEK_BUYUK)
            if r and r[0] >= ESIK_INCE and (r[0] - r[3]) >= 0.03:
                if harita == "Bakra_buyuk":
                    sonuc = (r[1] / bw, r[2] / bh, r[0], r[3], "ince", ESIK_INCE)
                else:
                    sonuc = ((BUYUK_BOLGE[0] + r[1] * s) / kw, (BUYUK_BOLGE[1] + r[2] * s) / kh, r[0], r[3], "ince", ESIK_INCE)
        # 2) kaba
        if sonuc is None and harita == "Bakra" and "Bakra" in c:
            r = None
            if kaba_pen is not None:
                r = _esle("Bakra", mini, OLCEK_BAKRA, kaba_pen)
                if r and r[0] < ESIK_KABA_PENCERE:
                    r = None
            if r is None:
                r = _esle("Bakra", mini, OLCEK_BAKRA)
                if r and (r[0] < ESIK_KABA or r[0] - r[3] < 0.04):
                    r = None
            if r:
                sonuc = (r[1] / kw, r[2] / kh, r[0], r[3], "kaba", ESIK_KABA)
        if sonuc is None:
            return None
        x, y, sk, ik, kay, esik = sonuc
        return {"x": round(float(x), 4), "y": round(float(y), 4), "guven": _guven(sk, ik, esik), "skor": round(float(sk), 3), "kaynak": kay}
    except Exception:
        return None


class EngelHafizasi:
    """Takilma noktalarini harita basina kalici tutar. Konumlar harita_konumu'nun dondurdugu oranlardir.
    Dosya: {harita: [[x, y, son_zaman, sayac], ...]} ; atomik yazim (gecici dosya + os.replace)."""

    def __init__(self, yol="engeller2.json", birlesme=0.01):
        self.yol = yol if os.path.isabs(yol) else os.path.join(KLASOR, yol)
        self.birlesme = birlesme
        self._k = threading.Lock()
        self.veri = {}
        try:
            with open(self.yol, encoding="utf-8") as f:
                v = json.load(f)
            if isinstance(v, dict):
                self.veri = v
        except Exception:
            self.veri = {}

    def _kaydet(self):
        try:
            tmp = self.yol + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.veri, f, ensure_ascii=False)
            os.replace(tmp, self.yol)
        except Exception as e:
            print("engel hafiza yazilamadi:", e)

    def ekle(self, harita, x, y):
        """Takilma noktasi ekle; birlesme yaricapi icinde kayit varsa sayaci artir (konumu agirlikli ortala). Sayaci dondurur."""
        with self._k:
            liste = self.veri.setdefault(harita, [])
            for e in liste:
                if math.hypot(e[0] - x, e[1] - y) < self.birlesme:
                    n = e[3]
                    e[0], e[1] = round((e[0] * n + x) / (n + 1), 4), round((e[1] * n + y) / (n + 1), 4)
                    e[2], e[3] = int(time.time()), n + 1
                    sayi = e[3]
                    break
            else:
                liste.append([round(float(x), 4), round(float(y), 4), int(time.time()), 1])
                sayi = 1
            self._kaydet()
            return sayi

    def engelli_mi(self, harita, x, y, yaricap=0.015):
        """Nokta bir engel kaydina yakin mi (sayaci >=2 olanlarda yaricap 1.5 kat)."""
        with self._k:
            for e in self.veri.get(harita, []):
                if math.hypot(e[0] - x, e[1] - y) < yaricap * (1.5 if e[3] >= 2 else 1.0):
                    return True
        return False

    def yol_engelli_mi(self, harita, x0, y0, x1, y1, yaricap=0.015):
        """(x0,y0)->(x1,y1) dogru parcasi bir engel noktasina yaricap'tan yakin geciyor mu. Baslangica
        (karakterin su an durdugu yere) yaricap/2'den yakin kayitlar yok sayilir."""
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        with self._k:
            for e in self.veri.get(harita, []):
                r = yaricap * (1.5 if e[3] >= 2 else 1.0)
                if math.hypot(e[0] - x0, e[1] - y0) < r / 2:
                    continue
                t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((e[0] - x0) * dx + (e[1] - y0) * dy) / L2))
                if math.hypot(e[0] - (x0 + t * dx), e[1] - (y0 + t * dy)) < r:
                    return True
        return False

    def eskit(self, gun=30):
        """gun'den eski VE tek seferlik (sayac<2) kayitlari sil. Silinen sayisini dondurur."""
        sinir = time.time() - gun * 86400
        n = 0
        with self._k:
            for h, liste in self.veri.items():
                yeni = [e for e in liste if not (e[2] < sinir and e[3] < 2)]
                n += len(liste) - len(yeni)
                liste[:] = yeni
            if n:
                self._kaydet()
        return n
