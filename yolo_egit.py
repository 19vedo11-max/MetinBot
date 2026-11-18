"""Sekil modeli (YOLO) icin otomatik isaretleme + egitim.

yolo_env\\Scripts\\python.exe yolo_egit.py hazirla   -> veri_yolo/ham karelerinden veri seti (etiketin altindaki govde = yaratik)
yolo_env\\Scripts\\python.exe yolo_egit.py egit      -> modeli egitir, sonucu model/yaratik.onnx olarak disari verir
yolo_env\\Scripts\\python.exe yolo_egit.py ornek     -> isaretlenmis birkac kareyi goruntu/yolo_ornek_*.jpg olarak kaydeder

Isaretleme: oyunun kirmizi yaratik adi (solunda yesil 'Lv') bulunur; adin hemen altindaki govde kutusu
ekrandaki yuksekliÄŸe gore (perspektif) tahmin edilir. Adi gorunmeyen uzak yaratiklar 'yok' sayilmasin diye
en ustteki etiketin yukarisi gri ile ortulur."""
import glob
import os
import random
import shutil
import sys

import cv2
import numpy as np

KLASOR = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KLASOR, "veri_yolo", "ham")
SET = os.path.join(KLASOR, "veri_yolo", "set")


def kirmizi_etiketler(k):
    """bot.py ile ayni kural (sade kopya): [(x_orta, y_alt, w, h)]"""
    r, g, b = k[..., 0].astype(int), k[..., 1].astype(int), k[..., 2].astype(int)
    m = (r > 120) & (r - g > 85) & (r - b > 75) & (g < 90)
    yk, gn = m.shape
    m[yk - 50:, :] = False                       # alt arayuz
    m[:200, gn - 200:] = False                   # mini harita
    m8 = cv2.dilate(m.astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_RECT, (13, 3)))
    n, _, ist, _ = cv2.connectedComponentsWithStats(m8, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, _ = ist[i]
        if 22 <= w <= 260 and 8 <= h <= 22:
            dolu = m[y:y + h, x:x + w].sum()
            if dolu >= 25 and dolu / (w * h) < 0.6:
                sol = k[y:y + h, max(0, x - 55):x].astype(int)
                if ((sol[..., 1] > 140) & (sol[..., 0] < 170) & (sol[..., 2] < 100)).sum() >= 8:
                    out.append((x + w // 2, y + h, w, h))
    return out


def govde_kutusu(x, y_alt, yk, gn):
    h = 25 + 0.11 * y_alt                         # perspektif: asagidaki (yakin) yaratik daha buyuk
    w = h * (0.9 + 0.0013 * y_alt)               # yakindakiler yandan daha uzun gorunur
    x0, y0, x1, y1 = x - w / 2, y_alt + 2, x + w / 2, y_alt + 2 + h
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(gn - 1, x1), min(yk - 51, y1)
    return x0, y0, x1, y1


def isaretle(yol):
    k = cv2.cvtColor(cv2.imread(yol), cv2.COLOR_BGR2RGB)
    yk, gn = k.shape[:2]
    et = kirmizi_etiketler(k)
    if not et:
        return None, None
    ust = max(0, min(t[1] - t[3] for t in et) - 40)
    k = k.copy()
    k[:ust] = 114                                 # adsiz uzak yaratiklar 'arka plan' sanilmasin
    k[yk - 50:] = 114
    kutular = [govde_kutusu(x, ya, yk, gn) for x, ya, _, _ in et]
    return k, [b for b in kutular if b[2] - b[0] > 10 and b[3] - b[1] > 10]


def hazirla():
    dosyalar = sorted(glob.glob(os.path.join(HAM, "*.jpg")))
    random.seed(1)
    random.shuffle(dosyalar)
    shutil.rmtree(SET, ignore_errors=True)
    for bol in ("train", "val"):
        os.makedirs(os.path.join(SET, "images", bol))
        os.makedirs(os.path.join(SET, "labels", bol))
    n_v = max(1, len(dosyalar) // 10)
    say = 0
    for i, f in enumerate(dosyalar):
        k, kutular = isaretle(f)
        if k is None:
            continue
        bol = "val" if i < n_v else "train"
        ad = os.path.splitext(os.path.basename(f))[0]
        cv2.imwrite(os.path.join(SET, "images", bol, ad + ".jpg"), cv2.cvtColor(k, cv2.COLOR_RGB2BGR))
        yk, gn = k.shape[:2]
        with open(os.path.join(SET, "labels", bol, ad + ".txt"), "w") as f_:
            for x0, y0, x1, y1 in kutular:
                f_.write(f"0 {(x0 + x1) / 2 / gn:.5f} {(y0 + y1) / 2 / yk:.5f} {(x1 - x0) / gn:.5f} {(y1 - y0) / yk:.5f}\n")
        say += 1
    with open(os.path.join(SET, "veri.yaml"), "w") as f_:
        f_.write(f"path: {SET}\ntrain: images/train\nval: images/val\nnames:\n  0: yaratik\n")
    print(f"veri seti: {say} kare (ham {len(dosyalar)})")


def ornek():
    for i, f in enumerate(sorted(glob.glob(os.path.join(HAM, "*.jpg")))[-4:]):
        k, kutular = isaretle(f)
        if k is None:
            continue
        for x0, y0, x1, y1 in kutular:
            cv2.rectangle(k, (int(x0), int(y0)), (int(x1), int(y1)), (0, 255, 255), 2)
        cv2.imwrite(os.path.join(KLASOR, "goruntu", f"yolo_ornek_{i}.jpg"), cv2.cvtColor(k, cv2.COLOR_RGB2BGR))
    print("ornekler goruntu/yolo_ornek_*.jpg")


def egit():
    set_ = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else SET
    from ultralytics import YOLO
    m = YOLO("yolo11n.pt")
    m.train(data=os.path.join(set_, "veri.yaml"), imgsz=960, epochs=80, batch=8, device=0, workers=2,
            project=os.path.join(KLASOR, "runs"), name="yaratik", exist_ok=True, patience=20,
            fliplr=0.5, mosaic=1.0, verbose=False)
    en_iyi = os.path.join(KLASOR, "runs", "yaratik", "weights", "best.pt")
    yol = YOLO(en_iyi).export(format="onnx", imgsz=960, dynamic=False)
    os.makedirs(os.path.join(KLASOR, "model"), exist_ok=True)
    shutil.copy(yol, os.path.join(KLASOR, "model", "yaratik.onnx"))
    print("model hazir: model/yaratik.onnx")


DUNYA_SINIF = ["wolf", "bear", "boar", "dog", "tiger", "monster", "animal"]
_dunya = []


def dunya_modeli():
    if not _dunya:
        from ultralytics import YOLOWorld
        m = YOLOWorld(os.path.join(KLASOR, "model", "hazir", "yolov8x-worldv2.pt"))
        m.set_classes(DUNYA_SINIF)
        _dunya.append(m)
    return _dunya[0]


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9)


def isaretle2(yol, esik=0.2):
    """Tum govde: acik sozluklu YOLO-World + adi gorunup World'un kacirdigi yaratik icin etiket-alti kutusu."""
    k = cv2.cvtColor(cv2.imread(yol), cv2.COLOR_BGR2RGB)
    yk, gn = k.shape[:2]
    r = dunya_modeli().predict(k[..., ::-1], imgsz=1280, conf=esik, verbose=False)[0]
    aday = sorted(((float(p),) + tuple(map(float, b)) for p, b in zip(r.boxes.conf, r.boxes.xyxy)), reverse=True)
    kutular = []
    for p, x0, y0, x1, y1 in aday:
        b = (x0, y0, x1, y1)
        if x1 - x0 < 12 or y1 - y0 < 12 or y0 > yk - 60 or (x0 > gn - 210 and y1 < 210):
            continue                                              # arayuz / mini harita / cok kucuk
        if x0 < gn / 2 < x1 and y0 < yk * 0.65 < y1 and y1 - y0 > 250:
            continue                                              # kendi karakterimiz
        if (x1 - x0) * (y1 - y0) > 0.25 * gn * yk:
            continue
        if any(_iou(b, c) > 0.5 for c in kutular):
            continue
        kutular.append(b)
    for x, ya, _, _ in kirmizi_etiketler(k):                      # adi var ama World gormedi
        if not any(c[0] - 20 < x < c[2] + 20 and -40 < c[1] - ya < 140 for c in kutular):
            g = govde_kutusu(x, ya, yk, gn)
            h_ = (g[3] - g[1]) * 1.6                               # eski kutu govdenin ust kismiydi: buyut
            kutular.append((g[0] - 0.2 * (g[2] - g[0]), g[1], g[2] + 0.2 * (g[2] - g[0]), min(yk - 51, g[1] + h_)))
    return k, kutular


def hazirla2():
    dosyalar = sorted(glob.glob(os.path.join(HAM, "*.jpg")))
    random.seed(1)
    random.shuffle(dosyalar)
    shutil.rmtree(SET, ignore_errors=True)
    for bol in ("train", "val"):
        os.makedirs(os.path.join(SET, "images", bol))
        os.makedirs(os.path.join(SET, "labels", bol))
    kontrol = os.path.join(KLASOR, "goruntu", "yolo_kontrol")
    shutil.rmtree(kontrol, ignore_errors=True)
    os.makedirs(kontrol)
    n_v = max(1, len(dosyalar) // 10)
    toplam = 0
    for i, f in enumerate(dosyalar):
        k, kutular = isaretle2(f)
        bol = "val" if i < n_v else "train"
        ad = os.path.splitext(os.path.basename(f))[0]
        shutil.copy(f, os.path.join(SET, "images", bol, ad + ".jpg"))
        yk, gn = k.shape[:2]
        with open(os.path.join(SET, "labels", bol, ad + ".txt"), "w") as f_:
            for x0, y0, x1, y1 in kutular:
                f_.write(f"0 {(x0 + x1) / 2 / gn:.5f} {(y0 + y1) / 2 / yk:.5f} {(x1 - x0) / gn:.5f} {(y1 - y0) / yk:.5f}\n")
        toplam += len(kutular)
        if i % 25 == 0:                                            # Vedat'in kontrolu icin ornek
            c = k.copy()
            for x0, y0, x1, y1 in kutular:
                cv2.rectangle(c, (int(x0), int(y0)), (int(x1), int(y1)), (255, 230, 0), 3)
            cv2.imwrite(os.path.join(kontrol, ad + ".jpg"), cv2.cvtColor(cv2.resize(c, (gn // 2, yk // 2)), cv2.COLOR_RGB2BGR))
        if i % 100 == 0:
            print(f"{i}/{len(dosyalar)} kare isaretlendi", flush=True)
    with open(os.path.join(SET, "veri.yaml"), "w") as f_:
        f_.write(f"path: {SET}\ntrain: images/train\nval: images/val\nnames:\n  0: yaratik\n")
    print(f"veri seti (tum govde): {len(dosyalar)} kare, {toplam} yaratik kutusu; kontrol ornekleri goruntu/yolo_kontrol")


# ---------------- hazirla3: DINO govde + ad etiketi eslemesi (6 sinif) ----------------
SET6 = os.path.join(KLASOR, "veri_yolo", "set6")
KONTROL = os.path.join(KLASOR, "veri_yolo", "kontrol")
SINIFLAR6 = ["yaratik", "metin", "npc", "oyuncu", "pazar", "esya"]
RENK6 = [(255, 80, 80), (255, 220, 0), (80, 200, 255), (80, 255, 80), (255, 0, 255), (255, 150, 0)]


def isaretle3(k):
    """RGB kare -> [(sinif_no, (x0,y0,x1,y1))]. DINO govdeleri + ad etiketleri."""
    import dino_isaretle
    import ad_siniflari
    yk, gn = k.shape[:2]
    govdeler = dino_isaretle.kutular(k)
    adlar = ad_siniflari.ad_etiketleri(k)
    sonuc = []

    def ekle(c, b):
        b = (max(0, b[0]), max(0, b[1]), min(gn - 1, b[2]), min(yk - 56, b[3]))
        if b[2] - b[0] < 8 or b[3] - b[1] < 8 or b[1] > yk - 55:
            return
        if b[0] > gn - 210 and b[3] < 210:
            return
        if any(_iou(b, o[1]) > 0.5 for o in sonuc):
            return
        sonuc.append((c, b))

    kullanilan = set()
    for g in govdeler:
        gb = (g["x0"], g["y0"], g["x1"], g["y1"])
        grup = g.get("grup")
        if grup == "pazar":
            continue
        en, ed = None, 1e9
        for i, a in enumerate(adlar):
            cx = (a["x0"] + a["x1"]) / 2
            if gb[0] - 30 <= cx <= gb[2] + 30 and gb[1] - 120 <= a["y1"] <= gb[1] + 40:
                d = abs(a["y1"] - gb[1])
                if d < ed:
                    en, ed = i, d
        if en is not None:
            kullanilan.add(en)
            s_ = adlar[en]["sinif"]
            if s_ in ("kendim", "evcil"):
                continue
            ekle(SINIFLAR6.index(s_), gb)
        elif grup == "yaratik" and (gb[2] - gb[0]) / max(1, gb[3] - gb[1]) <= 1.8:
            ekle(0, gb)
        elif grup == "metin":
            ekle(1, gb)
    for i, a in enumerate(adlar):
        if i in kullanilan:
            continue
        s_ = a["sinif"]
        if s_ == "yaratik":
            xo = (a["x0"] + a["x1"]) / 2
            g = govde_kutusu(xo, a["y1"], yk, gn)
            w = (g[2] - g[0]) * 1.4
            h = (g[3] - g[1]) * 1.6
            ekle(0, (xo - w / 2, g[1], xo + w / 2, g[1] + h))
        elif s_ == "esya":
            ekle(5, (a["x0"], a["y0"], a["x1"], a["y1"]))
        elif s_ == "pazar":
            ekle(4, (a["x0"], a["y0"], a["x1"], a["y1"]))
    tabelalar = [a for a in adlar if a["sinif"] == "pazar"]
    if tabelalar:
        for t in dino_isaretle.kutular(k, tezgah=True):
            if t.get("grup") != "pazar":
                continue
            for a in tabelalar:
                ox = min(t["x1"], a["x1"]) - max(t["x0"], a["x0"])
                if ox > 0 and 0 <= t["y0"] - a["y1"] <= 150:
                    ekle(4, (t["x0"], t["y0"], t["x1"], t["y1"]))
                    break
    return sonuc


def _yaz6(sonuc, yol, gn, yk):
    with open(yol, "w") as f_:
        for c, (x0, y0, x1, y1) in sonuc:
            f_.write(f"{c} {(x0 + x1) / 2 / gn:.5f} {(y0 + y1) / 2 / yk:.5f} {(x1 - x0) / gn:.5f} {(y1 - y0) / yk:.5f}\n")


def _cizim6(k, sonuc, yol):
    c = k.copy()
    for s_, (x0, y0, x1, y1) in sonuc:
        cv2.rectangle(c, (int(x0), int(y0)), (int(x1), int(y1)), RENK6[s_], 3)
        cv2.putText(c, SINIFLAR6[s_], (int(x0), max(14, int(y0) - 5)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, RENK6[s_], 2)
    yk, gn = c.shape[:2]
    cv2.imwrite(yol, cv2.cvtColor(cv2.resize(c, (gn // 2, yk // 2)), cv2.COLOR_RGB2BGR))


def dene3():
    dosyalar = sorted(glob.glob(os.path.join(HAM, "*.jpg")))
    sec = dosyalar[100:900:300][:3]
    cikti = os.path.join(KLASOR, "goruntu", "yolo_dene3")
    os.makedirs(cikti, exist_ok=True)
    say = [0] * 6
    for f in sec:
        k = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB)
        s_ = isaretle3(k)
        for c, _ in s_:
            say[c] += 1
        _cizim6(k, s_, os.path.join(cikti, os.path.basename(f)))
        print(os.path.basename(f), [SINIFLAR6[c] for c, _ in s_], flush=True)
    print("dene3 sayilar:", dict(zip(SINIFLAR6, say)))


def hazirla3():
    import json
    dosyalar = sorted(glob.glob(os.path.join(HAM, "*.jpg")))
    random.seed(1)
    random.shuffle(dosyalar)
    shutil.rmtree(SET6, ignore_errors=True)
    for bol in ("train", "val"):
        os.makedirs(os.path.join(SET6, "images", bol))
        os.makedirs(os.path.join(SET6, "labels", bol))
    ornek_k = os.path.join(KLASOR, "goruntu", "yolo_kontrol6")
    shutil.rmtree(ornek_k, ignore_errors=True)
    os.makedirs(ornek_k)
    n_v = max(1, len(dosyalar) // 10)
    say = [0] * 6
    sonuclar = {}
    for i, f in enumerate(dosyalar):
        k = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB)
        yk, gn = k.shape[:2]
        s_ = isaretle3(k)
        bol = "val" if i < n_v else "train"
        ad = os.path.splitext(os.path.basename(f))[0]
        shutil.copy(f, os.path.join(SET6, "images", bol, ad + ".jpg"))
        _yaz6(s_, os.path.join(SET6, "labels", bol, ad + ".txt"), gn, yk)
        for c, _ in s_:
            say[c] += 1
        sonuclar[f] = s_
        if i % 50 == 0:
            _cizim6(k, s_, os.path.join(ornek_k, ad + ".jpg"))
        if i % 100 == 0:
            print(f"{i}/{len(dosyalar)} kare isaretlendi", flush=True)
    with open(os.path.join(SET6, "veri.yaml"), "w") as f_:
        f_.write(f"path: {SET6}\ntrain: images/train\nval: images/val\nnames:\n"
                 + "".join(f"  {j}: {n}\n" for j, n in enumerate(SINIFLAR6)))
    shutil.rmtree(KONTROL, ignore_errors=True)
    os.makedirs(KONTROL)
    nadir = [f for f in dosyalar if any(c in (1, 2, 4, 5) for c, _ in sonuclar[f])]
    kume = set(nadir)
    diger = [f for f in dosyalar if f not in kume]
    random.seed(2)
    random.shuffle(nadir)
    random.shuffle(diger)
    for f in (nadir + diger)[:150]:
        ad = os.path.basename(f)
        shutil.copy(f, os.path.join(KONTROL, ad))
        sekiller = [{"label": SINIFLAR6[c], "points": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "group_id": None,
                     "description": "", "shape_type": "rectangle", "flags": {}} for c, (x0, y0, x1, y1) in sonuclar[f]]
        with open(os.path.join(KONTROL, os.path.splitext(ad)[0] + ".json"), "w", encoding="utf-8") as j:
            json.dump({"version": "4.3.3", "flags": {}, "shapes": sekiller, "imagePath": ad, "imageData": None,
                       "imageHeight": 1111, "imageWidth": 1920}, j, ensure_ascii=False, indent=2)
    with open(os.path.join(KONTROL, "classes.txt"), "w") as j:
        j.write("\n".join(SINIFLAR6) + "\n")
    print("hazirla3 bitti:", len(dosyalar), "kare; sinif kutulari:", dict(zip(SINIFLAR6, say)),
          "; kontrol:", min(150, len(dosyalar)), "kare", flush=True)


def kontrolden_al():
    import json
    guncel = 0
    klasor_ = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else KONTROL     # orn. veri_yolo\kontrol_yeni
    for j in sorted(glob.glob(os.path.join(klasor_, "*.json"))):
        ad = os.path.splitext(os.path.basename(j))[0]
        veri = json.load(open(j, encoding="utf-8"))
        gn, yk = veri.get("imageWidth", 1920), veri.get("imageHeight", 1111)
        yol = None
        for bol in ("train", "val"):
            if os.path.exists(os.path.join(SET6, "images", bol, ad + ".jpg")):
                yol = os.path.join(SET6, "labels", bol, ad + ".txt")
        if yol is None:
            continue
        s_ = []
        for sh in veri.get("shapes", []):
            if sh.get("label") not in SINIFLAR6:
                continue
            xs = [p[0] for p in sh["points"]]
            ys = [p[1] for p in sh["points"]]
            s_.append((SINIFLAR6.index(sh["label"]), (min(xs), min(ys), max(xs), max(ys))))
        _yaz6(s_, yol, gn, yk)
        guncel += 1
    print(f"kontrolden_al: {guncel} kare guncellendi")


if __name__ == "__main__":
    {"hazirla": hazirla, "hazirla2": hazirla2, "egit": egit, "ornek": ornek,
     "hazirla3": hazirla3, "dene3": dene3, "kontrolden_al": kontrolden_al}[sys.argv[1]]()
