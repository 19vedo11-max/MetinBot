"""MetinBot web paneli: tarayicida (bilgisayar ya da ayni Wi-Fi'deki telefon) botu izle ve yonet.

Calistir:  python web_panel.py   ->  http://localhost:8765
Telefondan: konsolda yazan adres (anahtar ile). Anahtar web_anahtar.txt dosyasinda; baskasi ayni agda olsa bile
anahtar olmadan hicbir seyi goremez/degistiremez."""
import ctypes
import json
import os
import secrets
import socket
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import kumanda
import siniflar

KLASOR = kumanda.KLASOR
WEB = os.path.join(KLASOR, "web")
PORT = int(os.environ.get("METINBOT_PORT", 8765))
for _i, _a in enumerate(sys.argv):          # python web_panel.py --port 8766
    if _a == "--port" and _i + 1 < len(sys.argv):
        PORT = int(sys.argv[_i + 1])

_yol_anahtar = os.path.join(KLASOR, "web_anahtar.txt")
if not os.path.exists(_yol_anahtar):
    with open(_yol_anahtar, "w") as f:
        f.write(secrets.token_urlsafe(9))
with open(_yol_anahtar) as f:
    ANAHTAR = f.read().strip()

# panelden degistirilebilen ayarlar (baska anahtar yazilmaz)
AYAR_IZINLI = {
    "kare_paylas_klasoru", "kare_paylas_adi", "kare_paylas_gunluk",
    "profil", "alan_kullan", "av_gorevi", "gorev_parsomen", "aranan_oncelik", "npc_gorevleri",
    "dusuk_seviye_kesme", "sadece_slot", "esyaya_tikla", "olunce_yeniden_basla", "yeniden_baglan",
    "beceri_puani_dagit", "pot_yuvasi_doldur", "metin_kes", "pot_satin_al", "pot_al_kirmizi_paket", "pot_al_mavi_paket", "pot_boy", "pot_paket", "pot_sira_kirmizi", "pot_sira_mavi", "patronlardan_kacin", "metin_ust_fark", "bildirim", "beceri_sira_yuva",
    "can_esigi", "mana_esigi", "seviye_ust_fark", "seviye_alt_fark", "slot_en_az", "savunma_can_esigi",
    "kasilma_alani", "toplanacak_grup", "statu", "esya_avi", "sadece_hedefler",
    "sinif", "beceri_grubu", "egitmen_anahtar", "sureli_tuslar", "saldiri_becerileri", "hamle_tusu", "saldiri_tusu",
    "can_potu_tusu", "mana_potu_tusu", "uzak_dovus", "beceri_puani_dagit",
}
KOMUT_IZINLI = {"duraklat", "devam", "kapat", "koy1", "koy2", "harita_kaydet", "harita_buyuk_kaydet", "pot_al", "yeniden_baslat"}


def _oku_csv(ad, n):
    yol = os.path.join(KLASOR, ad)
    if not os.path.exists(yol):
        return []
    with open(yol, encoding="utf-8", errors="replace") as f:
        return [s.strip().split(",") for s in f.readlines()[-n:] if s.strip()]


def _son_rapor():
    k = os.path.join(KLASOR, "rapor")
    if not os.path.isdir(k):
        return None
    md = sorted(f for f in os.listdir(k) if f.endswith(".md"))
    if not md:
        return None
    with open(os.path.join(k, md[-1]), encoding="utf-8") as f:
        return {"ad": md[-1][:-3], "metin": f.read()}


_VARSAYILAN = None


def _varsayilan():
    """bot.py'deki varsayilan ayarlar (ayar.json'da olmayan anahtarlar icin)."""
    global _VARSAYILAN
    if _VARSAYILAN is None:
        try:
            import ast
            with open(os.path.join(KLASOR, "bot.py"), encoding="utf-8") as f:
                agac = ast.parse(f.read())
            for n in agac.body:
                if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "VARSAYILAN":
                    _VARSAYILAN = ast.literal_eval(n.value)
        except Exception:
            _VARSAYILAN = {}
    return _VARSAYILAN or {}


def _json_oku(ad):
    try:
        with open(os.path.join(KLASOR, ad), encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def listeler():
    """Canavar ve esya secim listeleri (eski panelle ayni kaynak: harita_bilgisi.json, durum.json, esya_avi.json)."""
    haritalar = [{"ad": h.get("ad", "?"), "canavarlar": h.get("canavarlar", [])}
                 for h in _json_oku("harita_bilgisi.json").get("haritalar", []) if h.get("canavarlar")]
    gorulen = sorted({a for v in _json_oku("durum.json").get("bolge_ad", {}).values() for a in v
                      if len(a) >= 6 and not any(c.isdigit() for c in a)})
    esyalar = []
    for e in _json_oku("esya_avi.json").get("esyalar", []):
        esyalar.append({
            "ad": e.get("ad", ""), "kisaltma": e.get("kisaltma", ""), "kategori": e.get("kategori", "Diğer"),
            "sinif": e.get("sinif", ""), "seviye": e.get("seviye"), "tahmin": bool(e.get("tahmin")),
            "nereden": ", ".join(f"{k.get('ad')} (Lv {k.get('lv', '?')}, {k.get('harita', '?')})" for k in e.get("kaynaklar", [])),
        })
    return {"haritalar": haritalar, "gorulen": gorulen, "esyalar": esyalar}


def _son_30dk():
    try:
        import datetime as dt
        import gece_rapor
        simdi = dt.datetime.now()
        o, _ = gece_rapor.ozet(gece_rapor.satirlar_araliktaki(simdi - dt.timedelta(minutes=30), simdi), 30)
        return {k: o[k] for k in ("slot", "kesilen", "olum", "yer_degistirme")}
    except Exception:
        return None


def durum():
    d = kumanda.canli()
    a = dict(_varsayilan())
    a.update(kumanda.ayar_oku())
    haritalar = sorted(f[:-4] for f in os.listdir(os.path.join(KLASOR, "goruntu", "haritalar"))
                       if f.endswith(".png") and not f.startswith("mozaik_")) \
        if os.path.isdir(os.path.join(KLASOR, "goruntu", "haritalar")) else []
    try:
        panel_surum = os.path.getmtime(os.path.join(WEB, "index.html"))
    except OSError:
        panel_surum = 0
    return {
        "panel_surum": panel_surum,
        "canli": d,
        "ayar": {k: a.get(k) for k in AYAR_IZINLI},
        "profiller": [{"ad": k, "etiket": v, "aciklama": kumanda.PROFIL_ACIKLAMA.get(k, "")}
                      for k, v in kumanda.PROFILLER.items()],
        "log": kumanda.log_sonu(60),
        "exp": _oku_csv("exp_olcum.csv", 200),
        "rapor_ozet": _oku_csv(os.path.join("rapor", "ozet.csv"), 48),
        "son30": _son_30dk(),
        "son_rapor": _son_rapor(),
        "haritalar": haritalar,
        "simdi": time.time(),
    }


def botu_baslat():
    if kumanda.canli().get("ayakta"):
        kumanda.komut("devam")
        return "Bot zaten çalışıyor; devam ettirildi."
    bat = os.path.join(KLASOR, "Bot-Baslat.bat")
    sonuc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f'/c "{bat}"', KLASOR, 1)
    return "Bilgisayarda yönetici onayı istendi; onaylayınca bot açılır." if sonuc > 32 else "Bot başlatılamadı: yönetici onayı verilmedi."


class Isleyici(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _izinli(self):
        if self.client_address[0] in ("127.0.0.1", "::1"):
            return True
        q = parse_qs(urlparse(self.path).query)
        return q.get("k", [""])[0] == ANAHTAR or self.headers.get("X-Anahtar") == ANAHTAR

    def _gonder(self, kod, govde, tur="application/json; charset=utf-8"):
        if isinstance(govde, (dict, list)):
            govde = json.dumps(govde, ensure_ascii=False).encode("utf-8")
        elif isinstance(govde, str):
            govde = govde.encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        yol = urlparse(self.path).path
        if yol in ("/favicon.ico", "/amblem.png"):               # Vedo amblemi (anahtarsiz: yalniz resim)
            ad_ = "metinbot.ico" if yol.endswith(".ico") else "metinbot_amblem.png"
            with open(os.path.join(KLASOR, "araclar", ad_), "rb") as f:
                return self._gonder(200, f.read(), "image/x-icon" if ad_.endswith(".ico") else "image/png")
        if yol in ("/", "/index.html"):
            if not self._izinli():
                return self._gonder(403, "Anahtar gerekli: adresi bilgisayardaki konsoldan kopyala.", "text/plain; charset=utf-8")
            with open(os.path.join(WEB, "index.html"), "rb") as f:
                return self._gonder(200, f.read(), "text/html; charset=utf-8")
        if not self._izinli():
            return self._gonder(403, {"hata": "anahtar"})
        if yol == "/api/durum":
            return self._gonder(200, durum())
        if yol == "/api/siniflar":
            return self._gonder(200, siniflar.liste())
        if yol == "/api/listeler":
            return self._gonder(200, listeler())
        if yol.startswith("/harita/"):
            ad = os.path.basename(yol[len("/harita/"):]).replace("%20", " ")
            p = os.path.join(KLASOR, "goruntu", "haritalar", ad + ".png")
            if os.path.exists(p):
                with open(p, "rb") as f:
                    return self._gonder(200, f.read(), "image/png")
        if yol == "/api/olumler":                       # olum kara kutusu: son 10 kayit
            try:
                with open(os.path.join(KLASOR, "olum_defteri.csv"), encoding="utf-8") as f:
                    satir = [x.rstrip("\n").split(",") for x in f.readlines()[1:]][-10:]
                return self._gonder(200, {"olumler": [dict(zip(["zaman", "seviyem", "can", "yakin", "seviyeler", "pot", "mana", "alan"], x))
                                                      for x in reversed(satir)]})
            except Exception:
                return self._gonder(200, {"olumler": []})
        if yol == "/api/beceriler":
            try:
                with open(os.path.join(KLASOR, "beceriler.json"), encoding="utf-8") as f:
                    return self._gonder(200, json.load(f))
            except Exception:
                return self._gonder(200, {"siniflar": {}})
        if yol.startswith("/beceri/"):
            ad = os.path.basename(yol[len("/beceri/"):])
            uz = os.path.splitext(ad)[1].lower()
            tip = {".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}.get(uz)
            pb = os.path.join(KLASOR, "goruntu", "beceriler", ad)
            if tip and os.path.isfile(pb):
                with open(pb, "rb") as f:
                    return self._gonder(200, f.read(), tip)
        if yol == "/api/metinler":
            try:
                with open(os.path.join(KLASOR, "metinler.json"), encoding="utf-8") as f:
                    return self._gonder(200, json.load(f))
            except Exception:
                return self._gonder(200, {"metinler": []})
        if yol.startswith("/metin/"):
            ad = os.path.basename(yol[len("/metin/"):])
            uz = os.path.splitext(ad)[1].lower()
            tip = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}.get(uz)
            p = os.path.join(KLASOR, "goruntu", "metinler", ad)
            if tip and os.path.isfile(p):
                with open(p, "rb") as f:
                    return self._gonder(200, f.read(), tip)
        if yol == "/api/patronlar":
            try:
                with open(os.path.join(KLASOR, "patronlar.json"), encoding="utf-8") as f:
                    return self._gonder(200, json.load(f))
            except Exception:
                return self._gonder(200, {"patronlar": []})
        if yol.startswith("/patron/"):
            ad = os.path.basename(yol[len("/patron/"):])
            uz = os.path.splitext(ad)[1].lower()
            tip = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}.get(uz)
            p = os.path.join(KLASOR, "goruntu", "patronlar", ad)
            if tip and os.path.isfile(p):
                with open(p, "rb") as f:
                    return self._gonder(200, f.read(), tip)
        if yol == "/api/ekran":
            p = max((os.path.join(KLASOR, "goruntu", "izleme", f) for f in os.listdir(os.path.join(KLASOR, "goruntu", "izleme"))),
                    key=os.path.getmtime, default=None)
            if p:
                with open(p, "rb") as f:
                    return self._gonder(200, f.read(), "image/jpeg")
        return self._gonder(404, {"hata": "yok"})

    def do_POST(self):
        if not self._izinli():
            return self._gonder(403, {"hata": "anahtar"})
        yol = urlparse(self.path).path
        try:
            veri = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
        except Exception:
            return self._gonder(400, {"hata": "bozuk istek"})
        if yol == "/api/komut":
            k = veri.get("komut")
            if k == "baslat":
                return self._gonder(200, {"mesaj": botu_baslat()})
            if k not in KOMUT_IZINLI:
                return self._gonder(400, {"hata": "bilinmeyen komut"})
            if not kumanda.canli().get("ayakta"):
                return self._gonder(409, {"hata": "Bot kapalı. Önce botu başlat."})
            kumanda.komut(k)
            return self._gonder(200, {"mesaj": "gönderildi"})
        if yol == "/api/ayar":
            degisen = {k: v for k, v in veri.items() if k in AYAR_IZINLI}
            if not degisen:
                return self._gonder(400, {"hata": "değiştirilecek ayar yok"})
            kumanda.ayar_yaz(degisen)
            return self._gonder(200, {"mesaj": "kaydedildi"})
        if yol == "/api/git":
            if not kumanda.canli().get("ayakta"):
                return self._gonder(409, {"hata": "Bot kapalı. Önce botu başlat."})
            kumanda.git(str(veri.get("harita", "")), float(veri["x"]), float(veri["y"]))
            return self._gonder(200, {"mesaj": "gidiliyor"})
        return self._gonder(404, {"hata": "yok"})


def yerel_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    sunucu = ThreadingHTTPServer(("0.0.0.0", PORT), Isleyici)
    print(f"MetinBot paneli: http://localhost:{PORT}")
    print(f"Telefondan (ayni Wi-Fi): http://{yerel_ip()}:{PORT}/?k={ANAHTAR}")
    if "--acma" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    sunucu.serve_forever()


if __name__ == "__main__":
    main()
