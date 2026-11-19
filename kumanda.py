"""MetinBot kumandasi: paneli ve uzaktan (Claude) yonetimi ayni dosyalar uzerinden yapar.

Bot ile konusma yalniz dosyalarla olur (bot yonetici, panel/Claude degil):
  ayar.json   -> ayarlar + "profil" (bot degisikligi gorunce kendini yeniden acar)
  komut.json  -> tek seferlik komut: duraklat / devam / kapat (bot 2 sn'de bir bakar)
  canli.json  -> botun 2 sn'de bir yazdigi durum
  bot.log     -> gunluk

Komut satiri (uzaktan yonetim icin):
  python kumanda.py durum
  python kumanda.py profil toplama|level|metin|gorev
  python kumanda.py ayar av_gorevi true          (yaninda: av_gorevi, gorev_parsomen, aranan_oncelik, npc_gorevleri)
  python kumanda.py duraklat | devam | kapat
  python kumanda.py ayar <anahtar> <deger>      (deger JSON: true, 0.5, "str")
  python kumanda.py log [satir]
"""
import json
import os
import sys
import time

KLASOR = os.path.dirname(os.path.abspath(__file__))
PROFILLER = {          # ana iş; görevle ilgili dört ayar ayrıca seçilir (YANINDA)
    "toplama": "Yalnız otomatik toplama (ben oynuyorum)",
    "level": "Level kas",
    "metin": "Metin kes",
    "gorev": "Önce görevler",
    "yalniz_gorev": "Yalnız görev (kasılma yok)",
}
PROFIL_ACIKLAMA = {
    "toplama": "Bot hiçbir şeye vurmaz, yürümez; Z ile yere düşenleri toplar, can/mana düşünce kırmızı/mavi pot basar.",
    "level": "Seviyeme uygun slotları keser, metin taşı aramaz. Yanında ne yapacağını aşağıdan seç.",
    "metin": "Ekranda metin taşı görünce önce onu keser, yoksa slot keser. Yanında ne yapacağını aşağıdan seç.",
    "gorev": "Aşağıdaki dört görev işinin hepsi açık, NPC'lere sık gider; arada slot keser.",
    "yalniz_gorev": "Genel slot kesmez: görev listesini okur, NPC'lere (halkalılar dahil) gider, yalnız görevin istediği yaratığı keser; saldırana karşılık verir.",
}
BECERILER = {          # ayar adi -> ekranda gorunen ad (Yetenekler sekmesi, bedensel)
    "hava_kilici": "Hava Kılıcı",
    "ofke": "Öfke",
    "uc_yonlu": "Üç Yönlü Kesme",
    "kilic_cevirme": "Kılıç Çevirme",
    "hamle": "Hamle (3. satır sol)",
}
YANINDA = [            # (ayar anahtarı, etiket, açıklama)
    ("av_gorevi", "Av görevini de yap", "Av görevinin istediği yaratığı görünce önce onu keser."),
    ("gorev_parsomen", "Görev parşömenlerini aç", "Ödülleri alır, biten av görevinin yerine yenisini seçer."),
    ("aranan_oncelik", "Görev eşyası düşüren yaratığı öne al", "Örn. Biyolog'un çiçeği için Aç Alfa Kurt."),
    ("npc_gorevleri", "Görev NPC'lerine git ve konuş", "Haritada halkalı NPC'lere yürür; kasılmayı böler."),
]


def _yol(ad):
    return os.path.join(KLASOR, ad)


def ayar_oku():
    with open(_yol("ayar.json"), encoding="utf-8-sig") as f:
        return json.load(f)


def ayar_yaz(degisen):
    """ayar.json'da yalniz verilen anahtarlari degistirir (digerleri korunur), tek hamlede yazar."""
    ayar = ayar_oku()
    ayar.update(degisen)
    gecici = _yol("ayar.json.tmp")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(ayar, f, ensure_ascii=False, indent=2)
    os.replace(gecici, _yol("ayar.json"))
    return ayar


def komut(ad):
    if ad not in ("duraklat", "devam", "kapat", "arka_test", "beceri_goruntu", "bayrak_test", "bayrak_test2", "koy1", "koy2", "buyuk_harita_test", "yuru_test", "yuru_test2", "harita_kaydet", "harita_buyuk_kaydet", "satici_test", "pot_al", "envanter_foto", "pot_yuva_test", "yeniden_baslat"):
        raise ValueError("bilinmeyen komut: " + ad)
    gecici = _yol("komut.json.tmp")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump({"komut": ad, "zaman": time.time()}, f)
    os.replace(gecici, _yol("komut.json"))


def git(harita, x, y):
    """Bot o haritada (x, y: 0-1 arasi oran) isaretlenen noktaya yurusun."""
    gecici = _yol("komut.json.tmp")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump({"komut": "git", "harita": harita, "x": x, "y": y, "zaman": time.time()}, f, ensure_ascii=False)
    os.replace(gecici, _yol("komut.json"))


def canli():
    """Botun son yazdigi durum + 'ayakta' (son 8 sn icinde yazdi mi)."""
    try:
        with open(_yol("canli.json"), encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d["ayakta"] = bool(d.get("calisiyor")) and time.time() - d.get("zaman", 0) < 8
    return d


def durum_yazisi(d=None):
    d = d or canli()
    if not d.get("ayakta"):
        return "KAPALI"
    if d.get("duraklat"):
        return "DURAKLATILDI"
    if not d.get("oyun_onde"):
        return "BEKLİYOR (oyun penceresi önde değil)"
    return "ÇALIŞIYOR"


def log_sonu(n=25):
    try:
        with open(_yol("bot.log"), "rb") as f:
            f.seek(0, 2)
            boy = f.tell()
            f.seek(max(0, boy - 20000))
            satirlar = f.read().decode("utf-8", "replace").splitlines()
        return satirlar[-n:]
    except Exception:
        return []


def main(arg):
    if not arg or arg[0] == "durum":
        d = canli()
        print("durum   :", durum_yazisi(d))
        print("profil  :", ayar_oku().get("profil", "ozel"))
        if d.get("ayakta"):
            print("seviye  :", d.get("seviye"))
            print("kesilen :", d.get("kesilen"), f"({(time.time() - d.get('baslangic', time.time())) / 60:.0f} dk'da)")
            print("av hedefi:", ", ".join(d.get("av_hedefi") or []) or "-")
        print("--- son satirlar")
        print("\n".join(log_sonu(8)))
    elif arg[0] == "profil" and len(arg) > 1 and arg[1] in PROFILLER:
        ayar_yaz({"profil": arg[1]})
        print("profil ->", arg[1], "(bot kendini yeniden acacak)")
    elif arg[0] in ("duraklat", "devam", "kapat", "arka_test", "beceri_goruntu", "bayrak_test", "bayrak_test2", "koy1", "koy2", "buyuk_harita_test", "yuru_test", "yuru_test2", "harita_kaydet", "harita_buyuk_kaydet", "satici_test", "pot_al", "envanter_foto", "pot_yuva_test", "yeniden_baslat"):
        komut(arg[0])
        print("komut gonderildi:", arg[0])
    elif arg[0] == "ayar" and len(arg) > 2:
        try:
            deger = json.loads(arg[2])
        except Exception:
            deger = arg[2]
        ayar_yaz({arg[1]: deger})
        print(arg[1], "->", deger)
    elif arg[0] == "log":
        print("\n".join(log_sonu(int(arg[1]) if len(arg) > 1 else 30)))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
