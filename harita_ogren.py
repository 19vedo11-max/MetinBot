"""Mini haritadan bolgenin mozaigini kendisi cikaran + konum/kamera acisi/engel hafizasi. bot.py'den bagimsiz (cv2/numpy).

KULLANIM (bot.py'ye baglama):
    from harita_ogren import HaritaOgren
    ogren = HaritaOgren("Bakra")                 # mozaik_Bakra.png/.json varsa yukler
    ogren.besle(kare, time.time())               # her ~0.4 sn (tam ekran BGR kare)
    mx, my, guven = ogren.konum()                # mozaik pikseli (ya da None)
    th = ogren.kamera_acisi()                    # radyan (ekran 'yukari' yonunun harita acisi, y asagi) ya da None
    ogren.engel_ekle(ekran_aci=None)             # takilinca
    ogren.hedef_engelli_mi(ekran_dx, ekran_dy, ekran_mesafe_px)

KOORDINATLAR: mozaik pikseli, x sag, y asagi, kuzey yukari (mini harita donmez). 1 mozaik px = 1 mini harita px.
KAMERA ACISI: gorus konisinin merkezden gittigi yon, atan2(dy, dx) (y asagi). Ekranda 'yukari' = konin gittigi yon.
  Ekran vektoru (ex, ey) (x sag, y asagi) -> harita vektoru: (ex,ey) vektorunu t = kamera_acisi + pi/2 kadar dondur.
YONTEM: kirpinti (96x96, daire maske, ok/noktalar/koni maskeli) -> son konum etrafinda yuksek-gecirgen ozellikle maskeli
  sablon esleme -> mozaik (ortalama, sayac sinirli) -> zayifsa genis/tum mozaikte yeniden konumlanma.
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

MINI_MERKEZ_SAGDAN = 84
MINI_MERKEZ_Y = 86
K = 48                   # kirpinti yarim kenari (96x96); mini harita ic yaricapi ~54
DAIRE_R = 46             # kullanilan daire yaricapi
OK_R = 9                 # karakter oku maskesi yaricapi
N_TUVAL = 1200
SAYAC_SINIR = 12         # ortalama agirligi 1/(n+1), n en fazla bu
ESIK_IZLE = 0.50         # yakin arama kabul skoru
ESIK_TUM = 0.65          # genis/tum mozaik (yeniden konumlanma) kabul skoru
ESIK_MARJ = 0.04         # en iyi - ikinci tepe (genis aramada)
R_YAKIN = 26             # arama yaricapi (mozaik px)
R_GENIS = 64
EKRAN_PX_MOZAIK_PX = 25.0   # TAHMIN: 1 mozaik px ~ 25 ekran px (olculmedi); ogren.olcek ile degistirilir
ENGEL_YARICAP = 6.0         # TAHMIN: engel etki yaricapi (mozaik px)
ENGEL_ILERI = 8.0
KONI_YARI = math.radians(55)


def _daire(r, n=2 * K):
    y, x = np.mgrid[0:n, 0:n]
    return (((x - n / 2 + 0.5) ** 2 + (y - n / 2 + 0.5) ** 2) <= r * r)


_NB = 72
_DAIRE = _daire(DAIRE_R)
_YY, _XX = np.mgrid[0:2 * K, 0:2 * K]
_XR = (_XX - K + 0.5).astype(np.float32)
_YR = (_YY - K + 0.5).astype(np.float32)
_RAD = np.hypot(_XR, _YR)
_ANG = np.arctan2(_YR, _XR)


def _kirp(kare):
    h, w = kare.shape[:2]
    cx, cy = w - MINI_MERKEZ_SAGDAN, MINI_MERKEZ_Y
    if cx - K < 0 or cy - K < 0 or cy + K > h or cx + K > w:
        return None
    return kare[cy - K:cy + K, cx - K:cx + K]


def _kotu_maske(m):
    """Ok, kirmizi/sari/yesil/beyaz nokta ve simgeler (1=kotu), hafif genisletilmis."""
    b, g, r = [m[..., i].astype(np.int16) for i in range(3)]
    bad = ((r > 140) & (g < 90)) | ((r > 170) & (g > 140) & (b < 130)) | ((g > 150) & (r < 150) & (b < 120)) | \
          ((r > 150) & (g > 150) & (b > 150))
    bad = bad | ((r > g + 40) & (r > b + 40))        # kirmizi nokta kenarlari
    bad = cv2.dilate(bad.astype(np.uint8), np.ones((5, 5), np.uint8))
    bad[_RAD < OK_R] = 1
    return bad


def _hp(c, known, sg=4.0):
    """Maskeli yuksek gecirgen: c - yerel ortalama (yalniz bilinen piksellerden); bilinmeyen = 0."""
    k = known.astype(np.float32)
    num = cv2.GaussianBlur(c * k, (0, 0), sg)
    den = cv2.GaussianBlur(k, (0, 0), sg)
    return (c - num / np.maximum(den, 1e-3)) * k


def _ozellik(bgr, known):
    """Ham (yuksek gecirgensiz) gri ve yesil kanal, bilinen piksellerin ortalamasina gore ortalanmis; bilinmeyen = 0.
    (Mini harita cok puruzsuz: yuksek gecirgen ozellik dokuyu gurultuye indirip eslemeyi bozdu - olculdu.)"""
    f = bgr.astype(np.float32)
    b, g, r = cv2.split(f)
    k = known.astype(np.float32)
    n = max(float(k.sum()), 1.0)
    out = []
    for c in ((b + g + r) / 3, g):
        out.append((c - float((c * k).sum()) / n) * k)
    return out


class HaritaOgren:
    def __init__(self, harita="Bakra", klasor=HARITA_KLASOR, yukle=True):
        self.harita = harita
        self.klasor = klasor
        self.png = os.path.join(klasor, "mozaik_%s.png" % harita)
        self.js = os.path.join(klasor, "mozaik_%s.json" % harita)
        self.engel_yol = os.path.join(klasor, "mozaik_%s_engel.json" % harita)
        self.olcek = EKRAN_PX_MOZAIK_PX
        self.ort = np.zeros((N_TUVAL, N_TUVAL, 3), np.float32)
        self.say = np.zeros((N_TUVAL, N_TUVAL), np.float32)
        self.poz = None            # (x, y) son iyi konum
        self.guven_ = 0.0
        self.kayip = 0             # ardisik zayif kare
        self.n = 0
        self.kon_v = None          # koni yonu birim vektoru (EMA)
        self.kon_g = 0.0
        self.son_zaman = None
        self.t_ort = 0.0
        self._k = threading.Lock()
        self.engeller = []         # [x, y, zaman, sayac]
        self.bbox = None           # bilinen alan [x0,y0,x1,y1]
        self.son_skor = 0.0
        self.sicrama = 0
        if yukle:
            self._yukle()

    # ---------------------------------------------------------------- kalicilik
    def _yukle(self):
        try:
            im = cv2.imread(self.png, cv2.IMREAD_UNCHANGED)
            if im is not None and im.shape[:2] == (N_TUVAL, N_TUVAL) and im.shape[2] == 4:
                self.ort = im[..., :3].astype(np.float32)
                self.say = (im[..., 3] // 17).astype(np.float32)
            with open(self.js, encoding="utf-8") as f:
                m = json.load(f)
            if m.get("poz"):
                self.poz = tuple(m["poz"])
            self.n = m.get("n", 0)
            if m.get("kon_v"):
                self.kon_v = np.array(m["kon_v"], np.float32)
                self.kon_g = float(m.get("kon_g", 0.0))
        except Exception:
            pass
        try:
            with open(self.engel_yol, encoding="utf-8") as f:
                self.engeller = json.load(f)
        except Exception:
            self.engeller = []
        self._bbox_yenile()

    def _bbox_yenile(self):
        ys, xs = np.nonzero(self.say[::4, ::4] > 0)
        self.bbox = [int(xs.min()) * 4, int(ys.min()) * 4, int(xs.max()) * 4 + 4, int(ys.max()) * 4 + 4] if len(xs) else None

    def kaydet(self):
        try:
            os.makedirs(self.klasor, exist_ok=True)
            a = np.clip(self.say * 17, 0, 255).astype(np.uint8)
            im = np.dstack([np.clip(self.ort, 0, 255).astype(np.uint8), a])
            ys, xs = np.nonzero(a)
            tmp = self.png + ".tmp.png"
            cv2.imwrite(tmp, im)
            os.replace(tmp, self.png)
            meta = {"poz": list(self.poz) if self.poz else None, "n": self.n, "N": N_TUVAL, "zaman": int(time.time()),
                    "kon_v": self.kon_v.tolist() if self.kon_v is not None else None, "kon_g": self.kon_g,
                    "bilinen_px": int(len(xs)), "bbox": self.bbox, "kalite": round(self.guven_, 3)}
            with open(self.js + ".tmp", "w", encoding="utf-8") as f:
                json.dump(meta, f)
            os.replace(self.js + ".tmp", self.js)
            self._engel_kaydet()
        except Exception as e:
            print("mozaik yazilamadi:", e)

    def _engel_kaydet(self):
        try:
            with open(self.engel_yol + ".tmp", "w", encoding="utf-8") as f:
                json.dump(self.engeller, f)
            os.replace(self.engel_yol + ".tmp", self.engel_yol)
        except Exception as e:
            print("engel yazilamadi:", e)

    # ---------------------------------------------------------------- esleme
    def _esle(self, tf, tm, cx, cy, R, esik, kap=0.5):
        """(cx,cy) etrafinda +-R icinde esle -> (skor, x, y, ikinci) ya da None. Pencere mozaige kirpilir."""
        x0, y0 = int(cx - R - K), int(cy - R - K)
        x1, y1 = int(cx + R + K), int(cy + R + K)
        x0c, y0c = max(0, x0), max(0, y0)
        x1c, y1c = min(N_TUVAL, x1), min(N_TUVAL, y1)
        if x1c - x0c < 2 * K + 2 or y1c - y0c < 2 * K + 2:
            return None
        sayw = self.say[y0c:y1c, x0c:x1c]
        known = sayw > 0
        if known.sum() < 600:
            return None
        win = self.ort[y0c:y1c, x0c:x1c]
        wf = _ozellik(win, known)
        tot = 0
        for a, b in zip(wf, tf):
            tot = tot + cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED, mask=tm)
        tot = np.nan_to_num(tot / len(tf), nan=-1.0, posinf=-1.0, neginf=-1.0)
        # kapsama: sablon pikselinin kacinin mozaikte BILINEN yere denk dustugu (bilinmeyen = 0 yuzunden yanlis tepe uretmesin)
        cov = cv2.matchTemplate(known.astype(np.float32), tm, cv2.TM_CCORR) / max(float(tm.sum()), 1.0)
        tot = np.where(cov >= kap, tot, -1.0).astype(np.float32)
        _, mx, _, loc = cv2.minMaxLoc(tot)
        t2 = tot.copy()
        t2[max(0, loc[1] - 8):loc[1] + 9, max(0, loc[0] - 8):loc[0] + 9] = -1
        sec = float(t2.max())
        # alt piksel: parabola
        fx, fy = float(loc[0]), float(loc[1])
        try:
            if 0 < loc[0] < tot.shape[1] - 1:
                l, c, r = tot[loc[1], loc[0] - 1], tot[loc[1], loc[0]], tot[loc[1], loc[0] + 1]
                d = l - 2 * c + r
                if d < -1e-6:
                    fx += float(np.clip(0.5 * (l - r) / d, -0.5, 0.5))
            if 0 < loc[1] < tot.shape[0] - 1:
                u, c, dn = tot[loc[1] - 1, loc[0]], tot[loc[1], loc[0]], tot[loc[1] + 1, loc[0]]
                d = u - 2 * c + dn
                if d < -1e-6:
                    fy += float(np.clip(0.5 * (u - dn) / d, -0.5, 0.5))
        except Exception:
            pass
        return mx, fx + K + x0c, fy + K + y0c, sec

    def _tum_arama(self, tf, tm):
        """Bilinen alanin tamaminda ara (yeniden konumlanma)."""
        if self.bbox is None:
            return None
        bx0, by0, bx1, by1 = self.bbox
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        R = max(bx1 - bx0, by1 - by0) / 2 + 8
        r = self._esle(tf, tm, cx, cy, R, ESIK_TUM, 0.75)
        return r

    # ---------------------------------------------------------------- ana giris
    def besle(self, kare, zaman=None):
        """Bir mini harita kirpintisi isle. -> {"x","y","guven","skor","durum"} ya da None (kirpinti alinamadi)."""
        t0 = time.perf_counter()
        with self._k:
            try:
                return self._besle(kare, zaman)
            finally:
                dt = (time.perf_counter() - t0) * 1000
                self.t_ort = dt if self.t_ort == 0 else 0.95 * self.t_ort + 0.05 * dt

    def _besle(self, kare, zaman):
        crop = _kirp(kare)
        if crop is None:
            return None
        zaman = zaman if zaman is not None else time.time()
        bad = _kotu_maske(crop)
        clean0 = cv2.inpaint(crop, (bad > 0).astype(np.uint8), 3, cv2.INPAINT_TELEA)
        self._koni_tahmin(clean0, bad)
        # koni kama maskesi
        koni = np.zeros(bad.shape, bool)
        if self.kon_v is not None and self.kon_g > 0.35:
            a0 = math.atan2(self.kon_v[1], self.kon_v[0])
            da = np.abs((_ANG - a0 + math.pi) % (2 * math.pi) - math.pi)
            koni = (da < KONI_YARI) & (_RAD > OK_R)
        tmask = (_DAIRE & (bad == 0) & ~koni)
        # bad pikselleri komsu dokuyla doldur (ozellik hesabi icin)
        clean = clean0
        tf = _ozellik(clean, tmask)
        tm = tmask.astype(np.float32)
        durum = "yeni"
        sonuc = None
        if self.poz is None or self.say.max() == 0:
            sonuc = (1.0, N_TUVAL / 2, N_TUVAL / 2, 0.0)
            durum = "baslangic"
        else:
            r = self._esle(tf, tm, self.poz[0], self.poz[1], R_YAKIN, ESIK_IZLE) if self.kayip == 0 else None
            if r and r[0] >= ESIK_IZLE:
                sonuc, durum = r, "izle"
            else:
                # genis arama (son konum etrafinda) sonra tum mozaik
                r2 = self._esle(tf, tm, self.poz[0], self.poz[1], R_GENIS, ESIK_TUM, 0.75)
                if r2 and r2[0] >= ESIK_TUM and r2[0] - r2[3] >= ESIK_MARJ:
                    sonuc, durum = r2, "genis"
                elif self.kayip >= 2:
                    r3 = self._tum_arama(tf, tm)
                    if r3 and r3[0] >= ESIK_TUM and r3[0] - r3[3] >= ESIK_MARJ:
                        sonuc, durum = r3, "tum"
        if sonuc is None:
            self.kayip += 1
            self.guven_ = 0.0
            self.son_skor = float(r[0]) if (self.poz is not None and 'r' in dir() and r) else 0.0
            return {"x": self.poz[0] if self.poz else None, "y": self.poz[1] if self.poz else None, "guven": 0.0,
                    "skor": self.son_skor, "durum": "kayip"}
        skor, x, y, sec = sonuc
        if self.poz is not None and durum in ("genis", "tum"):
            self.sicrama += 1
        self.poz = (float(x), float(y))
        self.kayip = 0
        self.son_skor = float(skor)
        self.guven_ = float(max(0.0, min(1.0, (skor - 0.35) / 0.45)))
        self.n += 1
        self.son_zaman = zaman
        self._damga(crop, clean, tmask, x, y)
        return {"x": x, "y": y, "guven": round(self.guven_, 3), "skor": round(float(skor), 3), "durum": durum}

    # ---------------------------------------------------------------- mozaik yazma
    def _damga(self, crop, clean, tmask, x, y):
        ox, oy = int(round(x)) - K, int(round(y)) - K
        if ox < 0 or oy < 0 or ox + 2 * K > N_TUVAL or oy + 2 * K > N_TUVAL:
            return
        sl = (slice(oy, oy + 2 * K), slice(ox, ox + 2 * K))
        say = self.say[sl]
        ort = self.ort[sl]
        w = 1.0 / (np.minimum(say, SAYAC_SINIR) + 1.0)
        yaz = tmask
        # mevcut ortalamadan cok parlak sapma (koni/gecici nesne): yazma
        if self.n > 3:
            gk = clean.astype(np.float32).mean(axis=2)
            gm = ort.mean(axis=2)
            yaz = yaz & ~((say >= 2) & (np.abs(gk - gm) > 28))
        w = (w * yaz)[..., None]
        self.ort[sl] = ort * (1 - w) + clean.astype(np.float32) * w
        self.say[sl] = say + yaz
        if self.bbox is None:
            self.bbox = [ox, oy, ox + 2 * K, oy + 2 * K]
        else:
            b = self.bbox
            self.bbox = [min(b[0], ox), min(b[1], oy), max(b[2], ox + 2 * K), max(b[3], oy + 2 * K)]

    # ---------------------------------------------------------------- koni / kamera acisi
    def _koni_tahmin(self, clean, bad):
        """Kirpintidan DOGRUDAN koni yonu: halka ortalamasi cikarilmis parlaklik, aciya gore 72 dilim; 90 derece genis
        kutu sablonuyla (ic - dis ortalama) en yuksek kontrast. Mozaik gerektirmez. Kontrast<15 ise guvenilmez."""
        g = clean.astype(np.float32).mean(axis=2)
        ok = (_RAD > 14) & (_RAD < 44) & (bad == 0)
        rb = ((_RAD - 14) / 4).astype(np.int32)
        ab = (((_ANG + math.pi) / (2 * math.pi)) * _NB).astype(np.int32) % _NB
        rbo, abo, go = rb[ok], ab[ok], g[ok]
        rs = np.bincount(rbo, go, 8)
        rc = np.maximum(np.bincount(rbo, None, 8), 1)
        go = go - (rs / rc)[rbo]
        ps = np.bincount(abo, go, _NB)
        pc = np.bincount(abo, None, _NB).astype(np.float32)
        have = pc > 20
        P = np.where(have, ps / np.maximum(pc, 1), 0.0)
        n = _NB // 4
        best = None
        for st in range(_NB):
            idx = (np.arange(n) + st) % _NB
            ins = np.zeros(_NB, bool)
            ins[idx] = True
            if have[ins].sum() < n * 0.7 or have[~ins].sum() < 10:
                continue
            v = P[ins & have].mean() - P[~ins & have].mean()
            if best is None or v > best[0]:
                best = (v, (st + n / 2.0) % _NB)
        if best is None:
            return
        con, bi = best
        ang = (bi + 0.0) / _NB * 2 * math.pi - math.pi + math.pi / _NB * 0   # dilim merkezi (bi zaten dilim kenari+n/2)
        v = np.array([math.cos(ang), math.sin(ang)], np.float32)
        g_ = float(min(1.0, max(0.0, (con - 12) / 15.0)))
        if g_ <= 0:
            self.kon_g *= 0.9
            return
        if self.kon_v is None or self.kon_g < 0.1:
            self.kon_v, self.kon_g = v, g_
        else:
            nv = (1 - 0.6 * g_) * self.kon_v + 0.6 * g_ * v
            nn = float(np.hypot(*nv))
            self.kon_v = nv / nn if nn > 1e-6 else v
            self.kon_g = 0.6 * self.kon_g + 0.4 * g_

    def kamera_acisi(self):
        """Radyan (atan2(dy,dx), y asagi) ya da None. Ekran 'yukari'nin harita acisi."""
        if self.kon_v is None or self.kon_g < 0.3:
            return None
        return math.atan2(float(self.kon_v[1]), float(self.kon_v[0]))

    # ---------------------------------------------------------------- konum
    def konum(self):
        """(mx, my, guven) mozaik pikseli; henuz konum yoksa None."""
        if self.poz is None:
            return None
        return (self.poz[0], self.poz[1], self.guven_)

    # ---------------------------------------------------------------- engel
    def ekran_to_harita(self, ex, ey, th=None):
        """Ekran vektoru (x sag, y asagi) -> harita vektoru (ayni birimde)."""
        th = self.kamera_acisi() if th is None else th
        if th is None:
            return None
        t = th + math.pi / 2
        c, s = math.cos(t), math.sin(t)
        return ex * c - ey * s, ex * s + ey * c

    def engel_ekle(self, ekran_aci=None):
        """Karakterin (ve ekran_aci = takildigi yonun EKRAN acisi, atan2(dy,dx) verilirse ~8 px ilerisinin) konumunu
        engel olarak kaydet. -> sayac ya da None."""
        if self.poz is None or self.guven_ < 0.3:
            return None
        x, y = self.poz
        if ekran_aci is not None:
            v = self.ekran_to_harita(math.cos(ekran_aci), math.sin(ekran_aci))
            if v is not None:
                x, y = x + ENGEL_ILERI * v[0], y + ENGEL_ILERI * v[1]
        with self._k:
            for e in self.engeller:
                if math.hypot(e[0] - x, e[1] - y) < ENGEL_YARICAP * 0.6:
                    n = e[3]
                    e[0], e[1] = round((e[0] * n + x) / (n + 1), 2), round((e[1] * n + y) / (n + 1), 2)
                    e[2], e[3] = int(time.time()), n + 1
                    self._engel_kaydet()
                    return e[3]
            self.engeller.append([round(x, 2), round(y, 2), int(time.time()), 1])
            self._engel_kaydet()
            return 1

    def hedef_engelli_mi(self, ekran_dx, ekran_dy, ekran_mesafe_px=None, yaricap=None):
        """Karakterden ekran yonu (dx,dy) boyunca ekran_mesafe_px uzaktaki hedefe giden yol (haritada) bilinen bir
        engele yaricap'tan yakin geciyor mu. Kamera acisi/konum yoksa False. ekran_mesafe_px None ise vektor uzunlugu."""
        if self.poz is None or not self.engeller:
            return False
        L = math.hypot(ekran_dx, ekran_dy)
        if L < 1e-6:
            return False
        mesafe = L if ekran_mesafe_px is None else ekran_mesafe_px
        v = self.ekran_to_harita(ekran_dx / L, ekran_dy / L)
        if v is None:
            return False
        d = mesafe / self.olcek
        x0, y0 = self.poz
        x1, y1 = x0 + v[0] * d, y0 + v[1] * d
        yar = ENGEL_YARICAP if yaricap is None else yaricap
        ux, uy = v[0], v[1]
        for e in self.engeller:
            r = yar * (1.4 if e[3] >= 2 else 1.0)
            ex, ey = e[0] - x0, e[1] - y0
            along = ex * ux + ey * uy                 # yol boyunca ilerleme (px)
            if along < 2.0 or along > d + r:
                continue                              # arkada / yan / hedefin ilerisinde
            if abs(-ex * uy + ey * ux) < r:           # yol eksenine dik uzaklik
                return True
        return False

    def png_onizleme(self, yol, olcek=1.0):
        """Mozaigi (bilinen kutu) + konum + engeller ile PNG kaydet (hata ayiklama)."""
        if self.bbox is None:
            return
        x0, y0, x1, y1 = self.bbox
        im = np.clip(self.ort[y0:y1, x0:x1], 0, 255).astype(np.uint8).copy()
        im[self.say[y0:y1, x0:x1] == 0] = (40, 0, 40)
        for e in self.engeller:
            cv2.circle(im, (int(e[0] - x0), int(e[1] - y0)), int(ENGEL_YARICAP), (0, 0, 255), 1)
        if self.poz:
            cv2.circle(im, (int(self.poz[0] - x0), int(self.poz[1] - y0)), 3, (0, 255, 255), -1)
        if olcek != 1.0:
            im = cv2.resize(im, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(yol, im)
