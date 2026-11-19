"""Paylasim paketi uretir: dist/MetinBot-Paket-TARIH.zip  (calistir: python paylas.py)"""
import datetime as dt
import fnmatch
import json
import os
import zipfile

K = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(K, "dist")

KOK_DOSYA = ["Bot-Baslat.bat", "Kur.bat", "requirements.txt", "BENIOKU.md", "ayar_ornek.json",
             "harita_bilgisi.json", "esya_avi.json", "Panel.bat", "Web-Panel.bat"]
KOK_UZANTI = (".py", ".pyw", ".ps1")
ARAC = ["metinbot.ico", "metinbot_amblem.png", "KONTROL-NASIL.md"]
KLASOR = ["web", "sablon"]
YASAK_AD = [".env", "ayar.json", "engeller.json", "web_anahtar.txt", "canli.json", "durum.json", "komut.json", "pot_al.istek",
            "exp_olcum.csv", "*.log", "*.log.*", "*.pt", "*.onnx", "*.exe"]
YASAK_KLASOR = {"goruntu", "veri_yolo", "runs", "model", "yolo_env", "rapor", "_gecici", "dist", ".git",
                "__pycache__", "weights", "X-AnyLabeling", "kurulum", "xany_calisma"}


def ornek_ayar():
    with open(os.path.join(K, "ayar.json"), encoding="utf-8") as f:
        a = json.load(f)
    a["kasilma_alani"] = None
    a["alan_kullan"] = False
    a["sadece_hedefler"] = []
    a["esya_avi"] = ""
    a["profil"] = "level"
    with open(os.path.join(K, "ayar_ornek.json"), "w", encoding="utf-8") as f:
        json.dump(a, f, ensure_ascii=False, indent=2)


IZINLI_ALT = {("goruntu", "beceriler"), ("goruntu", "patronlar"), ("goruntu", "metinler")}   # panel simgeleri arkadaslara da gitsin


def yasak_mi(rel):
    parcalar = rel.replace("\\", "/").split("/")
    if len(parcalar) >= 3 and (parcalar[0], parcalar[1]) in IZINLI_ALT:
        return False
    if any(p in YASAK_KLASOR for p in parcalar[:-1]):
        return True
    return any(fnmatch.fnmatch(parcalar[-1].lower(), y.lower()) for y in YASAK_AD)


def topla():
    liste = []
    for ad in sorted(os.listdir(K)):
        yol = os.path.join(K, ad)
        if os.path.isfile(yol) and (ad in KOK_DOSYA or ad.endswith(KOK_UZANTI)):
            liste.append(ad)
    for ad in ARAC:
        if os.path.exists(os.path.join(K, "araclar", ad)):
            liste.append("araclar/" + ad)
    for ad in os.listdir(os.path.join(K, "araclar")):
        if ad.lower().endswith(".bat"):
            liste.append("araclar/" + ad)
    for kl in KLASOR:
        for kok, dirs, files in os.walk(os.path.join(K, kl)):
            dirs[:] = [d for d in dirs if d not in YASAK_KLASOR]
            for f in files:
                liste.append(os.path.relpath(os.path.join(kok, f), K).replace("\\", "/"))
    # ayar_ornek.json icin X-AnyLabeling-Kur.bat paketlenmez (kurucu indirir)
    liste = [r for r in dict.fromkeys(liste) if not yasak_mi(r) and "X-AnyLabeling" not in r]
    return liste


def main():
    ornek_ayar()
    os.makedirs(DIST, exist_ok=True)
    zip_yol = os.path.join(DIST, "MetinBot-Paket-%s.zip" % dt.date.today().isoformat())
    liste = topla()
    with zipfile.ZipFile(zip_yol, "w", zipfile.ZIP_DEFLATED) as z:
        for r in liste:
            z.write(os.path.join(K, r), "MetinBot/" + r)
    # dogrulama
    with zipfile.ZipFile(zip_yol) as z:
        adlar = [n[len("MetinBot/"):] for n in z.namelist()]
    kotu = [n for n in adlar if yasak_mi(n)]
    assert not kotu, "yasak dosya girdi: %s" % kotu
    print("zip:", zip_yol, "| dosya:", len(adlar), "| boyut KB:", os.path.getsize(zip_yol) // 1024)


if __name__ == "__main__":
    main()
