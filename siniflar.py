"""Sinif / beceri grubu hazir ayarlari (yalniz BASLANGIC onerisi; panelden tuslar degistirilir).

Beceri adlari Turkce Metin2 adlaridir; "tahmin" isaretliler dogrulanmadi, oyundaki adina gore duzelt.
Hizli cubuk: 1-4 ve F1-F4. 1 = kirmizi pot, 2 = mavi pot; beceriler 3, 4, F1..F4'e dizilir.
"""


def _b(tus, ad, tur, aralik=None, tahmin=True):
    d = {"tus": tus, "ad": ad, "tur": tur, "tahmin": tahmin}
    if aralik:
        d["aralik_sn"] = aralik
    return d


SINIFLAR = {
    "savasci": {"ad": "Savaşçı", "gruplar": {
        "bedensel": {"ad": "Bedensel", "statu": "str", "uzak_dovus": False, "tahmin": False, "beceriler": [
            _b("3", "Hava Kılıcı", "guclendirme", 55, False), _b("f3", "Öfke", "guclendirme", 55, False),
            _b("4", "Üç Yönlü Kesme", "saldiri", 6, False), _b("f1", "Kılıç Çevirme", "saldiri", 6, False),
            _b("f2", "Hamle", "hamle", None, False)]},
        "zihinsel": {"ad": "Zihinsel", "statu": "str", "uzak_dovus": False, "tahmin": True, "beceriler": [
            _b("3", "Güçlü Beden", "guclendirme", 55), _b("4", "Kılıç Darbesi", "saldiri", 6),
            _b("f1", "Ruh Vuruşu", "saldiri", 6), _b("f2", "Atılma", "hamle")]},
    }},
    "ninja": {"ad": "Ninja", "gruplar": {
        "yakin_dovus": {"ad": "Yakın dövüş (Suikastçı)", "statu": "dex", "uzak_dovus": False, "tahmin": True, "beceriler": [
            _b("3", "Pusu", "guclendirme", 55), _b("4", "Hızlı Saldırı", "saldiri", 6),
            _b("f1", "Hançer Fırtınası", "saldiri", 6), _b("f2", "Zehirli Bulut", "saldiri", 8)]},
        "uzak_dovus": {"ad": "Uzak dövüş (Okçu)", "statu": "dex", "uzak_dovus": True, "tahmin": True, "beceriler": [
            _b("3", "Hafif Adım", "guclendirme", 55), _b("4", "Tekrarlı Atış", "saldiri", 6),
            _b("f1", "Ok Yağmuru", "saldiri", 8), _b("f2", "Ateşli Ok", "saldiri", 6)]},
    }},
    "sura": {"ad": "Sura", "gruplar": {
        "buyulu_silah": {"ad": "Büyülü silah", "statu": "int", "uzak_dovus": False, "tahmin": True, "beceriler": [
            _b("3", "Büyülü Keskinlik", "guclendirme", 55), _b("4", "Parmak Darbesi", "saldiri", 6),
            _b("f1", "Ejderha Dönüşü", "saldiri", 6), _b("f2", "Korku", "saldiri", 8)]},
        "kara_buyu": {"ad": "Kara büyü", "statu": "int", "uzak_dovus": True, "tahmin": True, "beceriler": [
            _b("3", "Karanlık Koruma", "guclendirme", 55), _b("4", "Karanlık Küre", "saldiri", 6),
            _b("f1", "Alevli Vuruş", "saldiri", 6), _b("f2", "Ruh Patlaması", "saldiri", 8)]},
    }},
    "saman": {"ad": "Şaman", "gruplar": {
        "ejderha_gucu": {"ad": "Ejderha gücü", "statu": "int", "uzak_dovus": True, "tahmin": True, "beceriler": [
            _b("3", "Ejderha Gücü", "guclendirme", 55), _b("4", "Ejderha Atışı", "saldiri", 6),
            _b("f1", "Ejderha Kükremesi", "saldiri", 8), _b("f2", "Uçan Tılsım", "saldiri", 6)]},
        "iyilestirme": {"ad": "İyileştirme", "statu": "int", "uzak_dovus": True, "tahmin": True, "beceriler": [
            _b("3", "Hızlandırma", "guclendirme", 55), _b("f3", "Saldırı Değeri Artırma", "guclendirme", 55),
            _b("4", "Yıldırım Atışı", "saldiri", 6), _b("f1", "Uçan Tılsım", "saldiri", 6)]},
    }},
}


def hazir_ayar(sinif, grup):
    """ayar.json'a yazilacak onerilen degerler (yoksa None)."""
    g = SINIFLAR.get(sinif, {}).get("gruplar", {}).get(grup)
    if not g:
        return None
    b = g["beceriler"]
    ayar = {
        "sinif": sinif, "beceri_grubu": grup, "egitmen_anahtar": grup.split("_")[0],
        "statu": g["statu"], "uzak_dovus": bool(g["uzak_dovus"]),
        "saldiri_tusu": "space", "can_potu_tusu": "1", "mana_potu_tusu": "2",
        "sureli_tuslar": [{"tus": x["tus"], "aralik_sn": x["aralik_sn"]} for x in b if x["tur"] == "guclendirme"],
        "saldiri_becerileri": [{"tus": x["tus"], "aralik_sn": x["aralik_sn"]} for x in b if x["tur"] == "saldiri"],
        "hamle_tusu": "" if g["uzak_dovus"] else next((x["tus"] for x in b if x["tur"] == "hamle"), ""),
    }
    if sinif != "savasci":      # beceri puani konumlari (BECERI_KONUM) yalniz savasciya olculdu
        ayar["beceri_puani_dagit"] = False
    return ayar


def liste():
    """Panele sunulan duz liste (hazir ayarlar uretilmis halde)."""
    return [{"sinif": s, "sinif_ad": v["ad"], "grup": g, "grup_ad": gv["ad"], "tahmin": gv["tahmin"],
             "beceriler": gv["beceriler"], "ayar": hazir_ayar(s, g)}
            for s, v in SINIFLAR.items() for g, gv in v["gruplar"].items()]
