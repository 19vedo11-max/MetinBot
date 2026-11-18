"""Genel gorunum haritasindan yol bulma: su/kaya gecilmez, toprak yol ucuz, cayir pahali.

Oyun haritaya tiklaninca DUMDUZ yurutuyor (nehre, kayaya giriyor). Burada harita resmi siniflandirilir,
en ucuz rota bulunur ve rota, aralarinda engel olmayan ara duraklara indirgenir; bot bu duraklara sirayla tiklar.
"""
import heapq
import math

import cv2
import numpy as np

SU, KAYA, CAYIR, YOL = 0, 1, 2, 3
MALIYET = {YOL: 1.0, CAYIR: 5.0, KAYA: 40.0}      # su: gecilmez


def nokta_maskesi(p):
    """Harita ustune cizilen isaretler (yesil NPC noktalari, sari cekirdek, pembe halka, beyaz bayrak)."""
    p = p.astype(int)
    r, g, b = p[..., 0], p[..., 1], p[..., 2]
    yesil = (g > 170) & (r < 200) & (b < 150) & (g - b > 60)
    sari = (r > 200) & (g > 190) & (b < 120)
    pembe = (r > 170) & (r - g > 25) & (r - b > 25) & (g > 110) & (b > 100)
    beyaz = (r > 215) & (g > 215) & (b > 200)
    m = (yesil | sari | pembe | beyaz).astype(np.uint8)
    return cv2.dilate(m, np.ones((3, 3), np.uint8)) > 0


def siniflandir(p):
    """Harita resmi (RGB) -> sinif izgarasi. Isaretlerin altindaki zemin komsulardan doldurulur."""
    isaret = nokta_maskesi(p)
    temiz = cv2.inpaint(np.ascontiguousarray(p[..., ::-1]), isaret.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)[..., ::-1]
    q = cv2.GaussianBlur(temiz, (3, 3), 0).astype(int)
    r, g, b = q[..., 0], q[..., 1], q[..., 2]
    parlak = (r + g + b) / 3
    su = (b >= r + 6) & (b >= g - 12) & (parlak > 55) & (parlak < 150)
    # toprak yol doygun kahve (r-b ~50); kaya ayni tonda ama soluk (r-b ~29) -> esik 38
    yol = (r > g + 6) & (r - b >= 38) & (parlak > 55) & (parlak < 190)
    cayir = (g >= r) & (g > b + 6) & (parlak < 110)
    sinif = np.full(p.shape[:2], KAYA, np.uint8)       # acik gri kaya, koyu ucurum golgesi, kopru (gri)
    sinif[cayir] = CAYIR
    sinif[yol] = YOL
    sinif[su] = SU
    # tek piksellik gurultuyu temizle: su ve yol icin kucuk adaciklari at
    for s, en_az in ((SU, 12), (YOL, 5)):
        n, etiket, ist, _ = cv2.connectedComponentsWithStats((sinif == s).astype(np.uint8), 8)
        for i in range(1, n):
            if ist[i][4] < en_az:
                sinif[etiket == i] = CAYIR
    return sinif


def maliyet_izgarasi(sinif):
    m = np.full(sinif.shape, np.inf, np.float32)
    for s, c in MALIYET.items():
        m[sinif == s] = c
    # suya ve kayaya bitisik piksel biraz pahali: kiyidan/ucurum dibinden surtunerek gitmesin
    kotu = cv2.dilate(((sinif == SU) | (sinif == KAYA)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    m[kotu & np.isfinite(m) & (sinif != YOL)] += 4.0
    return m


def en_yakin_gecilir(m, nokta, yaricap=10):
    """Nokta gecilmez bir pikseldeyse (su, harita disi) en yakin gecilir pikseli dondurur."""
    x, y = int(nokta[0]), int(nokta[1])
    yuk, gen = m.shape
    en = None
    for dy in range(-yaricap, yaricap + 1):
        for dx in range(-yaricap, yaricap + 1):
            xx, yy = x + dx, y + dy
            if 0 <= xx < gen and 0 <= yy < yuk and np.isfinite(m[yy, xx]) and m[yy, xx] < 30:
                d = dx * dx + dy * dy
                if en is None or d < en[0]:
                    en = (d, xx, yy)
    return (en[1], en[2]) if en else None


def yol_bul(m, bas, hedef):
    """Dijkstra (8 komsu). bas/hedef = (x, y) harita pikseli. Donus: [(x, y), ...] ya da None."""
    yuk, gen = m.shape
    bas, hedef = en_yakin_gecilir(m, bas), en_yakin_gecilir(m, hedef)
    if not bas or not hedef:
        return None
    uzak = np.full(m.shape, np.inf, np.float32)
    once = {}
    uzak[bas[1], bas[0]] = 0
    kuyruk = [(0.0, bas)]
    komsu = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42)]
    while kuyruk:
        d, (x, y) = heapq.heappop(kuyruk)
        if (x, y) == hedef:
            break
        if d > uzak[y, x]:
            continue
        for dx, dy, boy in komsu:
            xx, yy = x + dx, y + dy
            if not (0 <= xx < gen and 0 <= yy < yuk):
                continue
            c = m[yy, xx]
            if not np.isfinite(c):
                continue
            if dx and dy and not (np.isfinite(m[y, xx]) and np.isfinite(m[yy, x])):
                continue                                # kose kesip sudan gecme
            nd = d + boy * c
            if nd < uzak[yy, xx]:
                uzak[yy, xx] = nd
                once[(xx, yy)] = (x, y)
                heapq.heappush(kuyruk, (nd, (xx, yy)))
    if hedef not in once and hedef != bas:
        return None
    rota, n = [hedef], hedef
    while n != bas:
        n = once[n]
        rota.append(n)
    return rota[::-1]


def _duz_gecilir(m, a, b, tavan):
    """a-b dogrusu uzerinde (1 piksel kenar payiyla) maliyeti tavani asan piksel var mi?"""
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) * 2 + 1
    yuk, gen = m.shape
    for i in range(n + 1):
        x = a[0] + (b[0] - a[0]) * i / n
        y = a[1] + (b[1] - a[1]) * i / n
        xi, yi = int(round(x)), int(round(y))
        if not (0 <= xi < gen and 0 <= yi < yuk) or m[yi, xi] > tavan:
            return False
    return True


def duraklar(m, rota, en_uzun=28):
    """Rotayi, aralarinda duz yurunebilen ara duraklara indirger (oyun iki durak arasini duz yurur).
    Bir parcanin izin verilen en pahali zemini, rotanin o parcada zaten kullandigi en pahali zemindir:
    yoldan giden parca cayira tasmaz, cayirdan giden parca kayaya/suya girmez."""
    if not rota:
        return []
    sonuc, i = [], 0
    while i < len(rota) - 1:
        j_en = i + 1
        tavan = float(m[rota[i + 1][1], rota[i + 1][0]])
        for j in range(i + 2, len(rota)):
            tavan = max(tavan, float(m[rota[j][1], rota[j][0]]))
            if math.hypot(rota[j][0] - rota[i][0], rota[j][1] - rota[i][1]) > en_uzun:
                break
            if _duz_gecilir(m, rota[i], rota[j], tavan):
                j_en = j
        sonuc.append(rota[j_en])
        i = j_en
    return sonuc


def oyuncu_bul(p, arka):
    """Oyuncu oku: arka plana (oyuncusuz harita) gore degisen krem renkli kucuk leke. Donus (x, y) ya da None."""
    if arka is None or arka.shape != p.shape:
        return None
    a, q = arka.astype(int), p.astype(int)
    fark = np.abs(q - a).sum(axis=2)
    r, g, b = q[..., 0], q[..., 1], q[..., 2]
    krem = (r > 185) & (g > 170) & (b > 90) & (b < 200) & (r - b > 30) & (g - b > 20)
    # koydeki NPC isaretleri ve yanip sonen pembe gorev halkalari oyuncu oku sanilmasin
    ar, ag, ab = a[..., 0], a[..., 1], a[..., 2]
    pembe = lambda x, y, z: (x > 160) & (x - y > 30) & (z >= y - 15) & (y > 90)  # noqa: E731  (ok krem: z << y)
    disla = pembe(r, g, b) | pembe(ar, ag, ab)
    disla |= (ag > 170) & (ar < 200) & (ab < 150) & (ag - ab > 60)               # yesil NPC noktasi (sabit)
    disla |= (ar > 200) & (ag > 190) & (ab < 120)                                # sari NPC cekirdegi (sabit)
    disla = cv2.dilate(disla.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    m = ((fark > 110) & krem & ~disla).astype(np.uint8)
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    n, _, ist, mer = cv2.connectedComponentsWithStats(m, 8)
    en = None
    for i in range(1, n):
        if 6 <= ist[i][4] <= 140 and (en is None or ist[i][4] > en[0]):
            en = (ist[i][4], mer[i])
    return (int(round(en[1][0])), int(round(en[1][1]))) if en else None


def arka_guncelle(yigin, p, en_cok=7):
    """Farkli anlarda alinmis harita karelerinin piksel ortancasi = oyuncusuz arka plan.
    Yigin karesi birbirinden cok farkliysa (baska harita) sifirlanir. Donus: (yigin, arka ya da None)."""
    if yigin and (yigin[-1].shape != p.shape or np.abs(yigin[-1].astype(int) - p.astype(int)).mean() > 25):
        yigin = []
    yigin = (yigin + [p.copy()])[-en_cok:]
    arka = np.median(np.stack(yigin), axis=0).astype(np.uint8) if len(yigin) >= 3 else None
    return yigin, arka


def ciz(p, sinif, rota=None, durak=None, oyuncu=None, olcek=3):
    """Hata ayiklama goruntusu (RGB): sinif renkleri + rota + duraklar."""
    renk = {SU: (40, 90, 200), KAYA: (150, 150, 150), CAYIR: (40, 110, 40), YOL: (190, 140, 70)}
    g = np.zeros(sinif.shape + (3,), np.uint8)
    for s, c in renk.items():
        g[sinif == s] = c
    g = cv2.resize(np.hstack([p, g]), None, fx=olcek, fy=olcek, interpolation=cv2.INTER_NEAREST)
    kay = p.shape[1] * olcek
    for x, y in rota or []:
        cv2.circle(g, (kay + x * olcek + 1, y * olcek + 1), 1, (255, 255, 255), -1)
    for x, y in durak or []:
        cv2.circle(g, (kay + x * olcek + 1, y * olcek + 1), 4, (255, 0, 255), 1)
    if oyuncu:
        cv2.circle(g, (kay + oyuncu[0] * olcek + 1, oyuncu[1] * olcek + 1), 5, (255, 255, 0), 2)
    return g
