"""Gece otomatik sekil modeli (YOLO) guncellemesi - Vedat'a is dusmez.

yolo_env\\Scripts\\python.exe gece_egit.py      (Gorev Zamanlayici her gece calistirir)

1. veri_yolo\\ham'daki yeni kareleri (bot oynarken kaydeder) Grounding DINO + ad renkleriyle isaretler
   (yolo_egit.isaretle3) ve veri_yolo\\set6'ya ekler; islenen kareler veri_yolo\\arsiv'e tasinir (ham dolmasin).
2. Son modelden (runs\\yaratik\\weights\\best.pt) ince ayar yapar (25 tur).
3. Eski ve yeni modeli ayni dogrulama karelerinde olcer; yeni model daha kotu degilse model\\yaratik.onnx'i gunceller.
4. Yeni karelerde model zayifsa (mAP50 < ESIK_KONTROL) veri_yolo\\kontrol_yeni'ye 30 kare koyar ve
   veri_yolo\\KONTROL_GEREKLI.txt yazar: o zaman Vedat X-AnyLabeling ile bakar (araclar\\Kontrol-Ac.bat yeni klasorle).
Her gece sonucu rapor\\yolo_gece.md'ye eklenir."""
import datetime as dt
import glob
import json
import os
import random
import shutil
import subprocess
import sys
import time

import cv2

import yolo_egit as Y

KLASOR = Y.KLASOR
SET6 = Y.SET6
DURUM = os.path.join(KLASOR, "veri_yolo", "gece_durum.json")
ARSIV = os.path.join(KLASOR, "veri_yolo", "arsiv")
KONTROL_YENI = os.path.join(KLASOR, "veri_yolo", "kontrol_yeni")
BAYRAK = os.path.join(KLASOR, "veri_yolo", "KONTROL_GEREKLI.txt")
RAPOR = os.path.join(KLASOR, "rapor", "yolo_gece.md")
KILIT = os.path.join(KLASOR, "veri_yolo", "gece_egit.kilit")
EN_AZ_YENI = 150          # bundan az yeni kare varsa bu gece egitme
EN_COK_YENI = 400         # bir calismada en cok bu kadar yeni kare isaretlenir (~1 sn/kare); gun icinde 3 saatte bir calisir
EN_COK_SET = 6000         # set6 bunu asarsa en eski egitim kareleri cikarilir
ESIK_KONTROL = 0.35       # yeni karelerde mAP50 bunun altindaysa Vedat'tan kontrol iste
TUR = 25
EN_COK_ARKADAS = 400      # bir gecede arkadas karelerinden en cok bu kadar (kendi kotasindan ayri)
EK_KAYNAKLAR = [os.path.join(os.environ["OneDrive"], "MetinBot-Kareler")] if os.environ.get("OneDrive") else []


def arkadas_kareleri():
    """EK_KAYNAKLAR altindaki kisi/gun/*.jpg (60 sn den eski) -> {kisi: [dosya]}."""
    kisiler = {}
    for kok in EK_KAYNAKLAR:
        if not os.path.isdir(kok):
            continue
        for f in glob.glob(os.path.join(kok, "*", "**", "*.jpg"), recursive=True):
            try:
                if time.time() - os.path.getmtime(f) <= 60:
                    continue
            except OSError:
                continue
            kisi = os.path.relpath(f, kok).split(os.sep)[0]
            kisiler.setdefault(kisi, []).append(f)
    return kisiler


def adil_dagit(kisiler, toplam):
    """Kisi basina esit pay; az olanin artani digerlerine gecer."""
    havuz = {k: random.sample(v, len(v)) for k, v in kisiler.items() if v}
    secim, sira = [], sorted(havuz)
    while len(secim) < toplam and any(havuz.values()):
        for k in sira:
            if havuz[k] and len(secim) < toplam:
                secim.append(havuz[k].pop())
    return secim


def arkadas_adi(f):
    for kok in EK_KAYNAKLAR:
        if f.startswith(kok):
            return os.path.relpath(f, kok).split(os.sep)[0]
    return "?"


def benzersiz_ad(f):
    """Arkadas karesi icin set/arsiv adi: kisi_gun_zaman (cakisma olmasin)."""
    for kok in EK_KAYNAKLAR:
        if f.startswith(kok):
            kisi, gun, zaman = (os.path.relpath(f, kok).split(os.sep) + ["", "", ""])[:3]
            return f"ark_{kisi}_{gun}_{os.path.splitext(os.path.basename(f))[0]}.jpg"
    return os.path.basename(f)


def kuru_say():
    ham = [f for f in glob.glob(os.path.join(Y.HAM, "*.jpg")) if time.time() - os.path.getmtime(f) > 60]
    ark = arkadas_kareleri()
    secilen = adil_dagit(ark, EN_COK_ARKADAS)
    print(f"kendi yeni kare: {len(ham)} (esik {EN_AZ_YENI}, gece en cok {EN_COK_YENI})")
    for k, v in sorted(ark.items()):
        print(f"arkadas {k}: {len(v)} kare bulundu, {sum(1 for f in secilen if arkadas_adi(f) == k)} secilecek")
    if not ark:
        print("arkadas karesi yok")


def _pythonw():
    p = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return p if os.path.exists(p) else sys.executable


def yaz(s):
    satir = f"{dt.datetime.now():%Y-%m-%d %H:%M}  {s}"
    print(satir, flush=True)
    os.makedirs(os.path.dirname(RAPOR), exist_ok=True)
    with open(RAPOR, "a", encoding="utf-8") as f:
        f.write(satir + "\n")


def baska_egitim_var():
    """Elle baslatilmis 'yolo_egit.py egit' calisiyor mu."""
    try:
        cikti = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
                                "ForEach-Object { $_.CommandLine }"], capture_output=True, text=True, timeout=60,
                               creationflags=0x08000000).stdout            # pencere acmasin (oyun onde kalsin)
        return any("yolo_egit.py" in s and " egit" in s for s in cikti.splitlines())
    except Exception:
        return False


def map50(model, yaml_):
    from ultralytics import YOLO
    r = YOLO(model).val(data=yaml_, imgsz=960, batch=8, device=0, workers=2, verbose=False, plots=False,
                        project=os.path.join(KLASOR, "runs"), name="gece_val", exist_ok=True)
    return float(r.box.map50)


def main():
    if os.path.exists(KILIT) and time.time() - os.path.getmtime(KILIT) < 6 * 3600:
        yaz("baska bir gece egitimi suruyor - atlandi")
        return
    if baska_egitim_var():
        yaz("elle baslatilmis bir egitim suruyor - bu gece atlandi")
        return
    open(KILIT, "w").close()
    # bellek darlasirsa botu kapat, egitim surer (Vedat'in izni)
    subprocess.Popen([_pythonw(), os.path.join(KLASOR, "bellek_bekci.py"), str(os.getpid()), "1200"],
                     cwd=KLASOR)
    try:
        calis()
    finally:
        try:
            os.remove(KILIT)
        except OSError:
            pass


def calis():
    durum = json.load(open(DURUM, encoding="utf-8")) if os.path.exists(DURUM) else {}
    os.makedirs(ARSIV, exist_ok=True)
    set_adlari = {os.path.basename(f) for f in glob.glob(os.path.join(SET6, "images", "*", "*.jpg"))}
    ham = sorted(glob.glob(os.path.join(Y.HAM, "*.jpg")))
    for f in [f for f in ham if os.path.basename(f) in set_adlari]:      # zaten sette olanlar: arsive
        shutil.move(f, os.path.join(ARSIV, os.path.basename(f)))
    yeni = [f for f in sorted(glob.glob(os.path.join(Y.HAM, "*.jpg"))) if time.time() - os.path.getmtime(f) > 60]
    random.seed(int(time.time()))
    ark_say = {}
    ark_sec = adil_dagit(arkadas_kareleri(), EN_COK_ARKADAS)
    for f in ark_sec:
        ark_say[arkadas_adi(f)] = ark_say.get(arkadas_adi(f), 0) + 1
    if len(yeni) + len(ark_sec) < EN_AZ_YENI:
        yaz(f"yeni kare az (kendi {len(yeni)} + arkadas {len(ark_sec)} < {EN_AZ_YENI}) - egitim yok")
        return
    random.shuffle(yeni)
    secilen, artan = yeni[:EN_COK_YENI], yeni[EN_COK_YENI:]
    if ark_sec:
        yaz(f"arkadas kareleri: kendi {len(secilen)}, arkadas {len(ark_sec)} (" +
            ", ".join(f"{k} {n}" for k, n in sorted(ark_say.items())) + ")")
        for f in ark_sec:                                  # ham'a kopyala (benzersiz ad), paylasimdan SIL
            try:
                hedef = os.path.join(Y.HAM, benzersiz_ad(f))
                shutil.copy(f, hedef)
                os.remove(f)
                secilen.append(hedef)
            except OSError as e:
                print("arkadas kare:", e)
    for f in artan:                                                      # fazlasi arsive (gerekirse sonra kullanilir)
        shutil.move(f, os.path.join(ARSIV, os.path.basename(f)))

    # 1) isaretle ve set6'ya ekle
    say = [0] * 6
    yeni_val = []
    sonuclar = {}
    for i, f in enumerate(secilen):
        k = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB)
        yk, gn = k.shape[:2]
        s_ = Y.isaretle3(k)
        bol = "val" if i % 10 == 0 else "train"
        ad = os.path.splitext(os.path.basename(f))[0]
        hedef = os.path.join(SET6, "images", bol, ad + ".jpg")
        shutil.copy(f, hedef)
        Y._yaz6(s_, os.path.join(SET6, "labels", bol, ad + ".txt"), gn, yk)
        if bol == "val":
            yeni_val.append(hedef)
        for c, _ in s_:
            say[c] += 1
        sonuclar[f] = s_
        if i % 100 == 0:
            print(f"{i}/{len(secilen)} kare isaretlendi", flush=True)
    yaz(f"{len(secilen)} yeni kare isaretlendi: " + ", ".join(f"{n} {a}" for a, n in zip(Y.SINIFLAR6, say)))

    # set cok buyurse en eski egitim karelerini cikar
    egitim = sorted(glob.glob(os.path.join(SET6, "images", "train", "*.jpg")))
    for f in egitim[:max(0, len(egitim) - EN_COK_SET)]:
        os.remove(f)
        etiket = f.replace(os.sep + "images" + os.sep, os.sep + "labels" + os.sep)[:-4] + ".txt"
        if os.path.exists(etiket):
            os.remove(etiket)

    # 2) ince ayar
    from ultralytics import YOLO
    yaml_ = os.path.join(SET6, "veri.yaml")
    onceki = os.path.join(KLASOR, "runs", "yaratik", "weights", "best.pt")
    if not os.path.exists(onceki):
        onceki = "yolo11n.pt"
    YOLO(onceki).train(data=yaml_, imgsz=960, epochs=TUR, batch=8, device=0, workers=2, patience=8,
                       project=os.path.join(KLASOR, "runs"), name="gece", exist_ok=True, fliplr=0.5, mosaic=1.0,
                       verbose=False, plots=False)
    yeni_m = os.path.join(KLASOR, "runs", "gece", "weights", "best.pt")

    # 3) karsilastir (ayni dogrulama kumesi) ve yeni karelerde ayri olc
    yeni_liste = os.path.join(KLASOR, "veri_yolo", "gece_yeni_val.txt")
    with open(yeni_liste, "w", encoding="utf-8") as f:
        f.write("\n".join(yeni_val) + "\n")
    yaml_yeni = os.path.join(KLASOR, "veri_yolo", "gece_yeni.yaml")
    with open(yaml_yeni, "w", encoding="utf-8") as f:
        f.write(f"path: {SET6}\ntrain: images/train\nval: {yeni_liste}\nnames:\n"
                + "".join(f"  {j}: {n}\n" for j, n in enumerate(Y.SINIFLAR6)))
    eski_tum = map50(onceki, yaml_) if onceki != "yolo11n.pt" else 0.0
    yeni_tum = map50(yeni_m, yaml_)
    yeni_yeni = map50(yeni_m, yaml_yeni)
    if yeni_tum >= eski_tum - 0.01:
        if os.path.exists(onceki):
            shutil.copy(onceki, os.path.join(KLASOR, "runs", "yaratik", "weights", f"best_{dt.date.today():%Y%m%d}_once.pt"))
        os.makedirs(os.path.join(KLASOR, "runs", "yaratik", "weights"), exist_ok=True)
        hedef_pt = os.path.join(KLASOR, "runs", "yaratik", "weights", "best.pt")
        shutil.copy(yeni_m, hedef_pt)
        yol = YOLO(hedef_pt).export(format="onnx", imgsz=960, dynamic=False)
        shutil.copy(yol, os.path.join(KLASOR, "model", "yaratik.onnx"))
        yaz(f"model GUNCELLENDI: tum dogrulama mAP50 {eski_tum:.3f} -> {yeni_tum:.3f}; yeni kareler {yeni_yeni:.3f}")
    else:
        yaz(f"yeni model daha kotu ({eski_tum:.3f} -> {yeni_tum:.3f}) - eski model korundu; yeni kareler {yeni_yeni:.3f}")

    # 4) yeni karelerde zayifsa Vedat'tan kontrol iste
    if yeni_yeni < ESIK_KONTROL:
        shutil.rmtree(KONTROL_YENI, ignore_errors=True)
        os.makedirs(KONTROL_YENI)
        for f in secilen[:30]:
            ad = os.path.basename(f)
            shutil.copy(f, os.path.join(KONTROL_YENI, ad))
            sekiller = [{"label": Y.SINIFLAR6[c], "points": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "group_id": None,
                         "description": "", "shape_type": "rectangle", "flags": {}} for c, (x0, y0, x1, y1) in sonuclar[f]]
            with open(os.path.join(KONTROL_YENI, os.path.splitext(ad)[0] + ".json"), "w", encoding="utf-8") as j:
                json.dump({"version": "4.3.3", "flags": {}, "shapes": sekiller, "imagePath": ad, "imageData": None,
                           "imageHeight": 1111, "imageWidth": 1920}, j, ensure_ascii=False, indent=2)
        with open(BAYRAK, "w", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M} yeni karelerde mAP50 {yeni_yeni:.3f} < {ESIK_KONTROL}: "
                    f"veri_yolo\\kontrol_yeni (30 kare) X-AnyLabeling ile kontrol edilmeli.\n")
        yaz(f"KONTROL GEREKLI: yeni karelerde model zayif ({yeni_yeni:.3f}); 30 kare veri_yolo\\kontrol_yeni'de")

    for f in secilen:                                                    # islenen ham kareler arsive
        if os.path.exists(f):
            shutil.move(f, os.path.join(ARSIV, os.path.basename(f)))
    durum.update(son=f"{dt.datetime.now():%Y-%m-%d %H:%M}", son_map50=yeni_tum, son_yeni_map50=yeni_yeni)
    json.dump(durum, open(DURUM, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    os.chdir(KLASOR)
    if "--kuru" in sys.argv:
        kuru_say()
        sys.exit(0)
    if sys.stdout is None or sys.stderr is None:                 # pythonw (Gorev Zamanlayici): cikti dosyaya
        _log = open(os.path.join(KLASOR, "gece_egit.log"), "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = _log
    main()
