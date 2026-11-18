"""Gorev yurutucu yardimcilari (saf mantik; bot.py'deki gorev_yurut() kullanir). gorev_tablosu.json'u okur."""
import difflib
import json
import os
import re
import time

import oku

KLASOR = os.path.dirname(os.path.abspath(__file__))
TABLO = os.path.join(KLASOR, "gorev_tablosu.json")
EKSIK = os.path.join(KLASOR, "gorev_tablosu_eksik.json")
_onbellek = {"mt": None, "veri": {}}
_GURULTU = ("durum", "yetenek", "duygu", "gorevler", "zaman", "tamamlandi")


def tablo_yukle():
    """Dosya degisince yeniden yukler; {anahtar: kayit}. '_' ile baslayan anahtarlar atlanir."""
    try:
        mt = os.path.getmtime(TABLO)
        if mt != _onbellek["mt"]:
            with open(TABLO, encoding="utf-8") as f:
                d = json.load(f)
            _onbellek["veri"] = {oku.sade(k): v for k, v in d.items() if not k.startswith("_") and isinstance(v, dict)}
            _onbellek["mt"] = mt
    except Exception:
        pass
    return _onbellek["veri"]


def _sade_baslik(b):
    s = oku.sade(b)
    s = re.sub(r"^ozel gorev ?", "", s)
    return s.strip()


def basliklari_ayir(yazi):
    """gorev_listesi() yazisindan [(sade baslik, kalan ya da None)]. Baslik = 'Zaman sinir...' satirindan onceki satir."""
    parcalar = [p.strip() for p in yazi.split(" | ")]
    sonuc = []
    for i, p in enumerate(parcalar):
        sd = oku.sade(p)
        if not (sd.startswith("zaman") and i > 0):
            continue
        onceki = parcalar[i - 1]
        if len(oku.sade(onceki).replace(" ", "")) < 4 or any(oku.sade(onceki).startswith(g) for g in _GURULTU):
            continue
        kalan = None
        if i + 1 < len(parcalar):
            m = re.match(r"kalan\s*(\d+)", oku.sade(parcalar[i + 1]))
            if m:
                kalan = int(m.group(1))
        sonuc.append((_sade_baslik(onceki), kalan))
    return sonuc


def esle(baslik, tablo, esik=0.75):
    """Sade basligi tablo anahtarina bulanik esler; yoksa None. 'av gorevi' on eki av anahtarina gider."""
    if not baslik:
        return None
    if baslik.startswith("av gorevi") and "av gorevi" in tablo:
        return "av gorevi"
    en, ek = None, 0.0
    for k in tablo:
        r = 1.0 if (k in baslik or baslik in k) and min(len(k), len(baslik)) >= 6 else difflib.SequenceMatcher(None, baslik, k).ratio()
        if r > ek:
            en, ek = k, r
    return en if ek >= esik else None


def eksik_yaz(baslik, metin):
    """Tabloda olmayan gorevi gorev_tablosu_eksik.json'a yazar (yineleme yok)."""
    try:
        d = {}
        if os.path.exists(EKSIK):
            with open(EKSIK, encoding="utf-8") as f:
                d = json.load(f)
        if baslik in d:
            return False
        d[baslik] = {"metin": metin, "gorulme": time.strftime("%Y-%m-%d %H:%M")}
        with open(EKSIK, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        return True
    except Exception:
        return False
