"""Gece raporu: bot.log'u belirli araliklarla ozetler ve rapor/ klasorune yazar.

python gece_rapor.py [aralik_dk=30] [bitis_saati=09:30]
Her rapor: son araliktaki slot, kesilen, olum, yer degistirme, takilma, duraklama nedenleri,
saatlik tecrube; ve otomatik "gelistirilecek" notlari (esiklere gore)."""
import collections
import datetime as dt
import os
import re
import sys
import time

KLASOR = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(KLASOR, "bot.log")
RAPOR = os.path.join(KLASOR, "rapor")
os.makedirs(RAPOR, exist_ok=True)


def satirlar_araliktaki(bas, bit):
    """bot.log'daki 'HH:MM:SS  ...' satirlarindan [bas, bit) arasindakiler (gece yarisi gecisi dikkate alinir)."""
    with open(LOG, encoding="utf-8", errors="replace") as f:
        tum = f.readlines()[-20000:]
    sonuc, gun, onceki = [], None, None
    for s in tum:
        b = re.search(r"bot basladi (\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)", s)
        if b:                                              # tarih yalniz baslik satirlarinda var
            gun = dt.datetime.strptime(b[1], "%Y-%m-%d").date()
            onceki = dt.datetime.strptime(b[1] + " " + b[2], "%Y-%m-%d %H:%M:%S")
            if bas <= onceki < bit:
                sonuc.append(s.rstrip())
            continue
        m = re.match(r"(\d\d):(\d\d):(\d\d)\s", s)
        if not m or gun is None:
            continue
        t = dt.datetime.combine(gun, dt.time(int(m[1]), int(m[2]), int(m[3])))
        if onceki and t < onceki - dt.timedelta(hours=1):   # gece yarisi gecti
            gun += dt.timedelta(days=1)
            t += dt.timedelta(days=1)
        onceki = t
        if bas <= t < bit:
            sonuc.append(s.rstrip())
    return sonuc


def ozet(sat, dk):
    say = lambda p: sum(1 for s in sat if re.search(p, s))
    kesilen = sum(int(m[1]) for s in sat for m in [re.search(r"grup: (\d+) canavar", s)] if m)
    durak = collections.Counter(m[1] for s in sat for m in [re.search(r"DURAKLAMA >3 sn: su an '([^']+)'", s)] if m)
    exp = [s for s in sat if "tecrube:" in s]
    d = {
        "slot": say(r"slot bitti"), "kesilen": kesilen, "olum": say(r"oldu \("),
        "yer_degistirme": say(r"bos yone gidiliyor|alan: cizilen|gezin: buyuk"),
        "atlandi": say(r"atlandi"), "engel": say(r"engel var"), "savunma": say(r"hasar aliyorum"),
        "dalma_yok": say(r"slotlara dalmiyor"), "ejderha": say(r"envanter: ejderha"),
        "pot_hata": say(r"pot yuvasi: .*konamadi"), "hata": say(r"Traceback|Error|hatasi"),
        "yeniden_baslama": say(r"bot basladi"), "baglanti": say(r"giris ekrani|baglanti koptu"),
        "metin": say(r"[Mm]etin"), "durak": durak, "exp": exp[-1] if exp else None,
    }
    notlar = []
    if d["olum"] >= max(3, dk // 10):
        notlar.append(f"Olum fazla ({d['olum']}/{dk} dk): bolge/seviye farki gozden gecirilmeli.")
    if d["slot"] and d["kesilen"] / d["slot"] < 1.5:
        notlar.append(f"Slot basina az kesim ({d['kesilen']}/{d['slot']}): grup bitince erken ayriliyor ya da sayim eksik.")
    if d["yer_degistirme"] > dk // 3:
        notlar.append(f"Cok yer degistirme ({d['yer_degistirme']}): hedef bulma/bolge secimi incelenmeli.")
    if d["engel"] or d["atlandi"] > dk // 2:
        notlar.append(f"Takilma ({d['atlandi']} atlama, {d['engel']} engel kacisi): yol bulma gelistirilmeli.")
    if durak:
        en, n = durak.most_common(1)[0]
        if n >= max(5, dk // 3):
            notlar.append(f"En cok duraklama: '{en}' ({n} kez) - hizlandirilmali.")
    if d["pot_hata"]:
        notlar.append(f"Pot yuvasi doldurulamadi ({d['pot_hata']} kez).")
    if d["hata"]:
        notlar.append(f"Kodda hata satiri: {d['hata']} - log incelenmeli.")
    if d["slot"] == 0 and d["olum"] == 0:
        notlar.append("Bu aralikta hic slot yok: bot duraklatilmis/kapali ya da hedef bulamiyor.")
    return d, notlar


def yaz(bas, bit, d, notlar):
    ad = os.path.join(RAPOR, bit.strftime("%Y%m%d_%H%M") + ".md")
    durak = ", ".join(f"{k} {v}" for k, v in d["durak"].most_common(5)) or "-"
    with open(ad, "w", encoding="utf-8") as f:
        f.write(f"# Gece raporu {bas:%H:%M}-{bit:%H:%M}\n\n")
        f.write(f"- Slot: {d['slot']} | kesilen: {d['kesilen']} | olum: {d['olum']} | savunma: {d['savunma']}\n")
        f.write(f"- Yer degistirme: {d['yer_degistirme']} | atlama: {d['atlandi']} | engel kacisi: {d['engel']} | dalma yok: {d['dalma_yok']}\n")
        f.write(f"- Ejderha basimi: {d['ejderha']} | pot hatasi: {d['pot_hata']} | hata: {d['hata']} | yeniden baslama: {d['yeniden_baslama']} | baglanti: {d['baglanti']}\n")
        f.write(f"- Tecrube: {d['exp'] or 'olculmedi'}\n")
        f.write(f"- Duraklama nedenleri: {durak}\n\n## Gelistirilecek\n")
        f.write("".join(f"- {n}\n" for n in notlar) or "- (esik asan bir sorun yok)\n")
    with open(os.path.join(RAPOR, "ozet.csv"), "a", encoding="utf-8") as f:
        f.write(f"{bit:%Y-%m-%d %H:%M},{d['slot']},{d['kesilen']},{d['olum']},{d['yer_degistirme']},{d['atlandi']},{d['engel']},{d['hata']}\n")
    print(f"{bit:%H:%M} rapor yazildi: {ad}", flush=True)


def main():
    dk = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    bitis = sys.argv[2] if len(sys.argv) > 2 else "09:30"
    hb, mb = map(int, bitis.split(":"))
    son = dt.datetime.now()
    while True:
        time.sleep(dk * 60)
        simdi = dt.datetime.now()
        d, notlar = ozet(satirlar_araliktaki(son, simdi), dk)
        yaz(son, simdi, d, notlar)
        son = simdi
        if (simdi.hour, simdi.minute) >= (hb, mb) and simdi.hour < 12:
            break


if __name__ == "__main__":
    main()
