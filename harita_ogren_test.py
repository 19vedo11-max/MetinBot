import glob, math, os, sys, time
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harita_ogren import HaritaOgren, N_TUVAL

K0 = os.path.dirname(os.path.abspath(__file__))
gec = os.path.join(K0, "_gecici")
os.makedirs(gec, exist_ok=True)


def calis(dosyalar, ad, og=None):
    og = og or HaritaOgren("TEST_" + ad, yukle=False)
    kayit = []
    for f in dosyalar:
        im = cv2.imread(f)
        if im is None:
            continue
        t = time.perf_counter()
        r = og.besle(im, time.time())
        dt = (time.perf_counter() - t) * 1000
        kayit.append((os.path.basename(f), r, dt, og.kamera_acisi()))
    return og, kayit


def ozet(ad, og, kayit):
    d = [k[1]["durum"] for k in kayit if k[1]]
    zam = np.array([k[2] for k in kayit])
    pos = [(k[1]["x"], k[1]["y"]) for k in kayit if k[1] and k[1]["x"] is not None]
    adim = [math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pos, pos[1:])]
    print("== %s: kare=%d  durum: %s" % (ad, len(kayit), {s: d.count(s) for s in set(d)}))
    print("   skor ort=%.3f min=%.3f | besle ms ort=%.1f medyan=%.1f p95=%.1f maks=%.1f" % (
        np.mean([k[1]["skor"] for k in kayit if k[1]]), min(k[1]["skor"] for k in kayit if k[1]), zam.mean(), np.median(zam),
        np.percentile(zam, 95), zam.max()))
    if adim:
        print("   adim px: ort=%.1f medyan=%.1f p95=%.1f maks=%.1f ; >30px sicrama=%d" % (
            np.mean(adim), np.median(adim), np.percentile(adim, 95), max(adim), sum(a > 30 for a in adim)))
    ac = [k[3] for k in kayit if k[3] is not None]
    if ac:
        v = np.array([(math.cos(a), math.sin(a)) for a in ac]).mean(0)
        print("   kamera acisi: %d/%d karede var; ort=%.0f derece, sirkuler guven=%.2f; ardisik fark ort=%.1f der" % (
            len(ac), len(kayit), math.degrees(math.atan2(v[1], v[0])), math.hypot(*v),
            np.mean([abs((b - a + math.pi) % (2 * math.pi) - math.pi) for a, b in zip(ac, ac[1:])]) * 180 / math.pi if len(ac) > 1 else 0))
    else:
        print("   kamera acisi: hic yok")
    print("   bilinen alan bbox:", og.bbox, "bilinen px:", int((og.say > 0).sum()))


if __name__ == "__main__":
    kayit_f = sorted(glob.glob(os.path.join(K0, "goruntu", "kayit", "k*.jpg")))
    og, kay = calis(kayit_f, "kayit")
    ozet("kayit", og, kay)
    og.png_onizleme(os.path.join(gec, "mozaik_test.png"), 3.0)
    for k in kay[:6] + kay[-3:]:
        print("  ", k[0], k[1]["durum"], round(k[1]["skor"], 2), "x=%.1f y=%.1f" % (k[1]["x"], k[1]["y"]), "aci=", None if k[3] is None else round(math.degrees(k[3])))
    # ikinci tur: ayni diziyi yeniden besle (bolgeye donus): ilk karede "tum" ile bulabilmeli
    og.poz = (og.poz[0] + 300, og.poz[1] - 250)   # bilerek yanlis konum -> yeniden konumlanma
    og.kayip = 3
    ok = 0
    ref = {k[0]: (k[1]["x"], k[1]["y"]) for k in kay}
    hata = []
    for f in kayit_f[::3]:
        im = cv2.imread(f)
        og.poz = (og.poz[0] + 200, og.poz[1] + 150) if False else (N_TUVAL / 2 + 400, N_TUVAL / 2 + 400)
        og.kayip = 3
        t = time.perf_counter()
        r = og.besle(im)
        dt = (time.perf_counter() - t) * 1000
        rx, ry = ref[os.path.basename(f)]
        e = math.hypot(r["x"] - rx, r["y"] - ry)
        hata.append((e, dt, r["durum"]))
    good = sum(1 for e, _, d in hata if e < 3)
    red = sum(1 for e, _, d in hata if d == "kayip")
    print("== yeniden konumlanma: dogru=%d yanlis=%d reddedilen(kayip)=%d / %d ; sure ort=%.0f ms maks=%.0f" % (
        good, len(hata) - good - red, red, len(hata), np.mean([h[1] for h in hata]), max(h[1] for h in hata)))
    # izleme dizisi
    izl = sorted(glob.glob(os.path.join(K0, "goruntu", "izleme", "*.jpg")))
    og2 = HaritaOgren("TEST_kayit", yukle=False)
    og2.ort, og2.say, og2.poz, og2.bbox, og2.n = og.ort.copy(), og.say.copy(), og.poz, og.bbox, og.n
    og2.kon_v, og2.kon_g = og.kon_v, og.kon_g
    og2.poz = (N_TUVAL / 2, N_TUVAL / 2)
    og2.kayip = 5
    d = []
    for f in izl:
        r = og2.besle(cv2.imread(f))
        d.append((os.path.basename(f), r["durum"], r["skor"], r["x"], r["y"]))
    print("== izleme (%d kare, kayit mozaigine karsi): durumlar %s" % (len(d), {s: [x[1] for x in d].count(s) for s in set(x[1] for x in d)}))
    for x in d[:12]:
        print("  ", x)
    og2.png_onizleme(os.path.join(gec, "mozaik_test_izleme.png"), 2.0)
