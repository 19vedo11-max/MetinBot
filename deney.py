"""Gece deneyleri: bot ayarlarini tek tek dene, 30 dk olc, iyiyse tut, kotuyse geri al.

python deney.py adim     -> (10 dk'da bir) aktif deney 30 dk'yi doldurduysa degerlendir; yoksa sirdakini baslat
python deney.py durum    -> kisa durum
Sonuclar: rapor/gece_gelistirme.md ; durum: deney_durum.json
Olcut: kesilen/saat (ana), olum/saat ve duraklama/saat (bozulmamali). Tek pencereli olcum gurultulu: tahmin."""
import datetime as dt
import json
import os
import re
import sys
import time

import gece_rapor
import kumanda

KLASOR = os.path.dirname(os.path.abspath(__file__))
DURUM = os.path.join(KLASOR, "deney_durum.json")
RAPOR = os.path.join(KLASOR, "rapor", "gece_gelistirme.md")
SURE_DK = 30

# Dusuk riskli, ayarla geri alinabilir deneyler (Vedat'in sectigi seviye/alan/slot/grup ayarlarina dokunulmaz)
SIRA = [
    ("ilk vurus beklemesi 5->4 sn", {"ilk_vurus_bekleme_sn": 4}),
    ("grup sonu can doldurma 2.5->1.5 sn", {"dolum_en_uzun_sn": 1.5}),
    ("grupta hasarsiz kalma 15->10 sn", {"grup_hasarsiz_sn": 10}),
    ("alana donus 25->15 sn", {"alan_bos_sn": 15}),
    ("kamera acisi 35->60 sn", {"kamera_egim_aralik_sn": 60}),
    ("etrafa bakma 1.25->2 sn", {"etrafa_bakma_sn": 2.0}),
    ("esya toplama 4->3 sn", {"toplama_en_uzun_sn": 3.0}),
    ("slot ici zincir yaricapi 240->300", {"spot_yaricapi_piksel": 300}),
    ("yolda dalma esigi 3->2", {"yolda_slot_en_az": 2}),
]


def durum_oku():
    try:
        return json.load(open(DURUM, encoding="utf-8"))
    except Exception:
        return {"aktif": None, "i": 0, "sonuc": []}


def durum_yaz(d):
    json.dump(d, open(DURUM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def metrik(bas, bit):
    sat = gece_rapor.satirlar_araliktaki(bas, bit)
    dk = max(1.0, (bit - bas).total_seconds() / 60)
    o, _ = gece_rapor.ozet(sat, int(dk))
    # duraklama: ham kuyruktan (zaman damgasiz 'DURAKLAMA bitti' satirlari)
    tum = open(gece_rapor.LOG, encoding="utf-8", errors="replace").read().splitlines()[-6000:]
    ds, icinde = 0.0, False
    b_s, e_s = bas.strftime("%H:%M:%S"), bit.strftime("%H:%M:%S")
    for s in tum:
        m = re.match(r"(\d\d:\d\d:\d\d)", s)
        if m:
            icinde = (b_s <= m[1] <= e_s) if b_s <= e_s else (m[1] >= b_s or m[1] <= e_s)
        m2 = re.search(r"DURAKLAMA bitti \(([\d.]+) sn\)", s)
        if m2 and icinde:
            ds += float(m2[1])
    k = 60 / dk
    return {"dk": round(dk), "kesilen_saat": round(o["kesilen"] * k), "slot_saat": round(o["slot"] * k),
            "olum_saat": round(o["olum"] * k, 1), "durak_saat": round(ds * k), "exp": o["exp"]}


def rapor(s):
    os.makedirs(os.path.dirname(RAPOR), exist_ok=True)
    yeni = not os.path.exists(RAPOR)
    with open(RAPOR, "a", encoding="utf-8") as f:
        if yeni:
            f.write("# Gece gelistirme deneyleri\n\nHer deney 30 dk; once/sonra kesilen/saat, olum/saat, duraklama sn/saat. "
                    "Tek pencere: gurultulu (tahmin).\n\n")
        f.write(s + "\n")


def adim():
    d = durum_oku()
    simdi = dt.datetime.now()
    a = d.get("aktif")
    if a:
        bas = dt.datetime.fromisoformat(a["bas"])
        gecen = (simdi - bas).total_seconds() / 60
        m = metrik(bas, simdi)
        erken_kotu = gecen >= 10 and m["olum_saat"] >= a["taban"]["olum_saat"] + 12   # olumler patladi: hemen geri al
        if gecen < SURE_DK and not erken_kotu:
            print(f"deney suruyor: {a['ad']} ({gecen:.0f}/{SURE_DK} dk) simdilik {m['kesilen_saat']}/saat "
                  f"(taban {a['taban']['kesilen_saat']}), olum {m['olum_saat']}/saat")
            return
        t = a["taban"]
        iyi = (m["kesilen_saat"] >= t["kesilen_saat"] * 1.03 and m["olum_saat"] <= t["olum_saat"] + 2
               and m["durak_saat"] <= t["durak_saat"] * 1.2 + 60) and not erken_kotu
        if not iyi:
            kumanda.ayar_yaz(a["onceki"])
        sonuc = "TUTULDU" if iyi else "GERI ALINDI"
        satir = (f"- {simdi:%H:%M} **{a['ad']}**: {sonuc}. kesilen/saat {t['kesilen_saat']} -> {m['kesilen_saat']}, "
                 f"olum/saat {t['olum_saat']} -> {m['olum_saat']}, duraklama sn/saat {t['durak_saat']} -> {m['durak_saat']}"
                 + (" (olumler artti, erken geri alindi)" if erken_kotu else ""))
        rapor(satir)
        d["sonuc"].append(satir)
        d["aktif"] = None
        durum_yaz(d)
        print(satir)
        return
    if d["i"] >= len(SIRA):
        print("deney sirasi bitti")
        return
    ad, degis = SIRA[d["i"]]
    ayar = kumanda.ayar_oku()
    import ast
    varsay = {}
    try:
        agac = ast.parse(open(os.path.join(KLASOR, "bot.py"), encoding="utf-8").read())
        for n in agac.body:
            if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "VARSAYILAN":
                varsay = ast.literal_eval(n.value)
    except Exception:
        pass
    onceki = {k: ayar.get(k, varsay.get(k)) for k in degis}
    taban = metrik(simdi - dt.timedelta(minutes=SURE_DK), simdi)
    kumanda.ayar_yaz(degis)
    d["aktif"] = {"ad": ad, "bas": simdi.isoformat(), "onceki": onceki, "yeni": degis, "taban": taban}
    d["i"] += 1
    durum_yaz(d)
    print(f"deney basladi: {ad} | taban {taban['kesilen_saat']} kesilen/saat, olum {taban['olum_saat']}/saat, "
          f"duraklama {taban['durak_saat']} sn/saat")


if __name__ == "__main__":
    os.chdir(KLASOR)
    {"adim": adim, "durum": lambda: print(json.dumps(durum_oku(), ensure_ascii=False)[:600])}[sys.argv[1] if len(sys.argv) > 1 else "durum"]()
