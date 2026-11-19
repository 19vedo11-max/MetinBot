"""konum.harita_konumu testi: goruntu/izleme'deki en yeni ~60 kare. Kullanim: python konum_test.py [kare_sayisi]"""
import math, os, sys, time
import cv2, numpy as np
import konum

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
kl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goruntu", "izleme")
fs = sorted(os.listdir(kl), key=lambda f: os.path.getmtime(os.path.join(kl, f)))[-N:]
konum.harita_konumu(cv2.imread(os.path.join(kl, fs[0])))   # onbellek isinmasi (haritalar yuklenir)
sonuc, sureler = [], []
for f in fs:
    k = cv2.imread(os.path.join(kl, f))
    if k is None or k.mean() < 10:
        continue
    t0 = time.perf_counter()
    r = konum.harita_konumu(k)
    sureler.append((time.perf_counter() - t0) * 1000)
    sonuc.append((f, r))
ok = [(f, r) for f, r in sonuc if r]
print(f"kare {len(sonuc)}  konum bulunan {len(ok)}  (%{100*len(ok)/max(1,len(sonuc)):.0f})  ince {sum(r['kaynak']=='ince' for _,r in ok)}  kaba {sum(r['kaynak']=='kaba' for _,r in ok)}")
print(f"sure ms: ort {np.mean(sureler):.1f}  medyan {np.median(sureler):.1f}  maks {np.max(sureler):.1f}")
if ok:
    g = np.array([r["guven"] for _, r in ok]); print(f"guven ort {g.mean():.2f}  >=0.5: {(g>=0.5).sum()}")
# ardisik tutarlilik (kareler dakikalar arayla; yalniz yuksek guvenli konumlar arasi)
yuksek = [(f, r) for f, r in ok if r["guven"] >= 0.4]
mes = [math.hypot((a[1]["x"] - b[1]["x"]) * 316, (a[1]["y"] - b[1]["y"]) * 318) for a, b in zip(yuksek, yuksek[1:])]
if mes:
    print(f"guven>=0.4 konum {len(yuksek)}; ardisik mesafe (Bakra px) medyan {np.median(mes):.0f}, >60 px sicrama {sum(m>60 for m in mes)}/{len(mes)}")
# izleme modu: onceki konum verilerek (gercek kullanim)
onc, s2, ayni = None, [], 0
for f, r0 in sonuc:
    k = cv2.imread(os.path.join(kl, f))
    t0 = time.perf_counter(); r = konum.harita_konumu(k, onceki=onc); s2.append((time.perf_counter() - t0) * 1000)
    if r: onc = (r["x"], r["y"])
print(f"onceki= ile ort sure {np.mean(s2):.1f} ms")
# cizim
B = cv2.imread(os.path.join(konum.HARITA_KLASOR, "Bakra.png"))
S = 3
B = cv2.resize(B, None, fx=S, fy=S, interpolation=cv2.INTER_CUBIC)
prev = None
for i, (f, r) in enumerate(ok):
    p = (int(r["x"] * 316 * S), int(r["y"] * 318 * S))
    renk = (0, 255, 255) if r["guven"] >= 0.4 else (160, 160, 160)
    if prev and r["guven"] >= 0.4 and prev[1]:
        cv2.line(B, prev[0], p, (255, 120, 0), 1)
    cv2.circle(B, p, 4, renk, -1); cv2.putText(B, str(i), (p[0] + 4, p[1] - 4), 0, 0.4, (255, 255, 255), 1)
    prev = (p, r["guven"] >= 0.4)
os.makedirs("_gecici", exist_ok=True)
cv2.imwrite("_gecici/konum_iz.png", B)
print("yazildi _gecici/konum_iz.png")
