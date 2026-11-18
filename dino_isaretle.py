"""Grounding DINO ile egitim verisi isaretleme (bot icinde KULLANILMAZ; yavas, yalniz veri seti icin).

yolo_env\\Scripts\\python.exe dino_isaretle.py <kare.jpg> [cikti.jpg] [--tezgah]   -> kutulari yazar / cizer

Kod icinden:
    from dino_isaretle import kutular
    for b in kutular(rgb):          # rgb: HxWx3 uint8 RGB, 1920x1111 oyun karesi
        b["x0"], b["y0"], b["x1"], b["y1"], b["skor"], b["ifade"], b["grup"]
    grup: yaratik (hayvan/canavar ifadesi) | insan (person: oyuncu, insansi yaratik, NPC) | metin | pazar
    Son YOLO sinifini grup DEGIL ad etiketinin rengi belirlemeli (kirmizi ad = yaratik, vb.); DINO govde kutusunu verir.

Model: IDEA-Research/grounding-dino-base (model/hazir/grounding-dino-base), GPU fp16, ~1.1 GB VRAM.

Ayar (2026-11-18, 19 oyun karesinde denenerek):
  * Ana gecis tek istem: "wolf. bear. boar. tiger. dog. monster. animal. person." kutu esigi 0.25, yazi esigi 0.20,
    800 px kisa kenar. Dogal boyutta (1111 px) model bozuluyor (19 karede >0.12 skorlu toplam 56 kutu; 800 px'te 918).
  * Ifadeler ayni istemde birlesince zayif ifade eziliyor: metin tasi tek istemde 'animal' (0.13-0.50) etiketi aliyor,
    'crystal rock' / 'glowing rock' tasta hic kazanmiyor. Bu yuzden tas AYRI ve TEK ifadeyle aranir.
  * Metin tasi: tam karede 'crystal rock' taslarda 0.33-0.51, tassiz karelerde de 0.40'a cikiyor (ayrilmiyor).
    Beyaz adli (solunda yesil Lv) etiketin altindaki 400x320 kirpintida 'crystal rock' 7/7 tasi 0.44-0.91 ile buldu;
    konum kosulu (etiketin 0-130 px alti, yatayda +-70 px) ile esik 0.40.
  * Pazar: 'market stall' pazarda 0 kutu, koyde yurt/araba kutuluyor (kullanilmaz); 'sign'/'signboard' tabelalarin
    cogunu kaciriyor. 'table' tek ifade pazarda yakin tezgah govdelerini dogru buluyor (122157: esik 0.30 denemede
    17/17 dogru, son ayarda esik 0.33 + suzgec 12/12 dogru; uzaktaki onlarca tezgahi kaciriyor), 19 karenin diger
    17'sinde 0 kutu, koyde (030629) 2 yanlis (NPC tezgahi, araba). Varsayilan KAPALI (tezgah=True ile acilir).
    Pazar sinifi (tabela kutusu) icin kural tabanli tabela bulucu daha uygun.
  * Hiz (RTX 5050, fp16, model yuklu; baska CPU surecleri calisirken): ana gecis 0.54-0.71 sn/kare; kutular() toplam
    60 rastgele ham karede ort 0.98 sn (medyan 0.97, en cok 1.67) -> 1015 kare ~17 dk. Pencere sablonu ~0.13-0.20 sn;
    tas kirpintisi yalniz beyaz etiket varsa (kare basina ort 0.025 kez) +~0.6 sn. Model yukleme 3-22 sn (disk onbellegi).
    Tepe VRAM 1.1 GB. YOLO-World (imgsz 1280) 0.155 sn/kare.

OLCUM (2026-11-18, 19 cesitli kare gozle sayildi; goruntu/dino_test/<kare>_dino|_world|_karsilastir.jpg):
  Kareler: sisli cayir kurt surusu, kalabalik insansi yaratik, tepeden kamera + cesetler + acik envanter, koy (tezgah
  arkasinda yigin), gol kiyisi yakin dev ayi, uzak suruler, sonbahar, su kenari, pagoda koyu, pazar (yaratik yok),
  yakin kamera, karanlik, 5 metin tasli kare.  Gercek yaratik (gorunur govde) toplam 374.
                       bulunan        kacan  yanlis kutu  ceset kutusu
    DINO (bu dosya)    345 (%92)       29       21           15
    YOLO-World yalniz   95 (%25)      279        4            3
    isaretle2 (World + etiket-alti ek kutu)
                       125 (%33)      249       48            3
  Kare kare (gercek | DINO bulunan/yanlis | World bulunan/yanlis | isaretle2 bulunan/yanlis):
    013003 sisli cayir kurt     38 | 37/2 | 13/0 | 13/3     015541 kalabalik asker   38 | 35/3 |  0/0 | 11/7
    021920 tepeden kamera        3 |  3/1 |  0/0 |  2/1     030629 koy yigin          5 |  2/0 |  3/1 |  3/2
    031944 gol kiyisi           23 | 16/2 |  4/0 |  4/3     035200 ayi + metin        6 |  6/1 |  4/1 |  4/1
    040156 uzak suruler         21 | 19/2 | 12/0 | 12/1     074114 sonbahar asker    19 | 17/3 |  1/0 |  2/7
    085046 su kenari            35 | 32/0 |  7/0 |  8/1     101428 kalabalik+kaplan  37 | 37/1 |  3/0 | 12/3
    102345 pagoda koyu          15 | 14/0 |  0/0 |  3/3     122157 pazar              0 |  0/0 |  0/0 |  0/2
    133713 yakin kamera         11 | 10/0 |  5/0 |  5/1     134934 karanlik           4 |  4/0 |  4/0 |  4/0
    082438 yamac + metin        38 | 38/0 |  6/0 |  6/3     012504 kurt+domuz+les    35 | 33/2 | 19/1 | 19/2
    084917 vadi + 2 metin       25 | 22/2 |  6/1 |  6/5     091926 yamac + metin     14 | 13/2 |  5/0 |  5/2
    031721 kumsal + metin        7 |  7/0 |  3/0 |  6/1
  World'un dusuk sayisi buyuk olcude insansi yaratiklardan (asker/okcu): isaretle2 sinif listesinde 'person' yok,
  World onlari hic kutulamiyor. World + 'person' denenmedi.
  DINO yanlis kutularin dokumu (21): 8 cift/parca kutu, 5 kendi evcilimiz (SaMRicKeTs - Kursun Asker), 4 sahne nesnesi
    (2 top arabasi, kaya, binek ati), 2 grup kutusu, 1 kendi karakter parcasi ('animal' etiketli), 1 metin tasi 'animal'.
  DINO kacan (29): 13 ust uste/arkada kalan (6'si grup kutusu icinde: iskelede 4, kurt kumesinde 2), 8 uzak/minik ya da
    kenarda yarim, 6 arayuz maskesinde (sagdaki etkinlik simgesi bolgesi), 1 esik alti (0.25), 1 kendi karakter
    suzgecinde silinen (karakterin hemen yanindaki insansi yaratik).
  Metin tasi: 8 tasin 6'si 'metin' (0 yanlis metin kutusu); 1'i ana geciste 'animal', 1'i kurtlarin arkasinda bulunamadi.
  Insan: oyuncu/NPC 8 kutu 'person' (dogru kutu); pazarda uzaktaki onlarca oyuncuyu kaciriyor.
  Bilinen zaaflar: insansi yaratik, oyuncu ve NPC hepsi 'person' (ayirmak icin ad rengi sart; kirmizi adli PK oyuncu
    ve 'Zalim' unvanli oyuncu da kirmizi). Yerde yatan cesetler kutulaniyor (15). Evcilimiz kutulaniyor. Ust uste
    hayvanlarda tek grup/cift kutu. Tezgahi (pazar tabelasi) DINO bulmuyor.
"""
import os
import sys
import time

import cv2
import numpy as np

KLASOR = os.path.dirname(os.path.abspath(__file__))
MODEL_YOLU = os.path.join(KLASOR, "model", "hazir", "grounding-dino-base")

# ana gecis: ifade -> grup
IFADELER = {
    "wolf": "yaratik", "bear": "yaratik", "boar": "yaratik", "tiger": "yaratik", "dog": "yaratik",
    "monster": "yaratik", "animal": "yaratik",
    "person": "insan",
}
KUTU_ESIK = 0.25      # box_threshold: sorgunun en yuksek token olasiligi
YAZI_ESIK = 0.20      # text_threshold: kazanan ifadenin token olasiligi
KISA_KENAR = 800      # islenen goruntu boyu (modelin egitildigi olcek; buyutmek bozuyor)
UZUN_KENAR = 1333
NMS_ESIK = 0.5

TAS_IFADE = "crystal rock"    # yalniz beyaz etiketin altindaki kirpintida
TAS_ESIK = 0.40
TEZGAH_IFADE = "table"        # istege bagli pazar gecisi (tam kare)
TEZGAH_ESIK = 0.33

_m = {}


def _yukle():
    if not _m:
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
        cihaz = "cuda" if torch.cuda.is_available() else "cpu"
        tur = torch.float16 if cihaz == "cuda" else torch.float32
        _m["islem"] = AutoProcessor.from_pretrained(MODEL_YOLU)
        _m["model"] = AutoModelForZeroShotObjectDetection.from_pretrained(MODEL_YOLU, dtype=tur).to(cihaz).eval()
        _m["cihaz"], _m["tur"], _m["torch"] = cihaz, tur, torch
    return _m


def _metin_ve_araliklar(ifadeler):
    """'wolf. bear. ...' metni + her ifadenin karakter araligi"""
    parca, ara, i = [], [], 0
    for f in ifadeler:
        ara.append((i, i + len(f)))
        parca.append(f)
        i += len(f) + 2
    return ". ".join(parca) + ".", ara


def _iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9)


def _icinde(a, b):
    """a kutusunun ne kadari b'nin icinde (0-1)"""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / ((a[2] - a[0]) * (a[3] - a[1]) + 1e-9)


def _k(b):
    return b["x0"], b["y0"], b["x1"], b["y1"]


def ham_kutular(rgb, ifadeler=None, kutu_esik=None, yazi_esik=None, kisa=None, uzun=None):
    """Modelin suzulmemis cikisi: [dict(x0,y0,x1,y1,skor,ifade)] (NMS yok).
    Etiket: her sorgu icin ifadelerin token olasiliklarinin en buyugu (argmax); HF'nin birlesik
    'wolf bear' gibi etiketleri yerine her kutuya tek ifade dusur."""
    m = _yukle()
    torch = m["torch"]
    ifadeler = list(ifadeler or IFADELER)
    kutu_esik = KUTU_ESIK if kutu_esik is None else kutu_esik
    yazi_esik = YAZI_ESIK if yazi_esik is None else yazi_esik
    metin, ara = _metin_ve_araliklar(ifadeler)
    yk, gn = rgb.shape[:2]
    boy = {"shortest_edge": kisa or KISA_KENAR, "longest_edge": uzun or UZUN_KENAR}
    g = m["islem"](images=rgb, text=metin, return_tensors="pt", return_offsets_mapping=True, size=boy)
    ofs = g.pop("offset_mapping")[0].tolist()
    g = {k: (v.to(m["cihaz"], m["tur"]) if v.is_floating_point() else v.to(m["cihaz"])) for k, v in g.items()}
    with torch.inference_mode():
        c = m["model"](**g)
    olas = c.logits[0].float().sigmoid().cpu().numpy()          # (900, 256)
    kut = c.pred_boxes[0].float().cpu().numpy()                 # (900, 4) cx cy w h (0-1)
    tok = [[j for j, (a, b) in enumerate(ofs) if b > a and a >= s and b <= e] for s, e in ara]
    ifade_ol = np.stack([olas[:, t].max(axis=1) if t else np.zeros(len(olas)) for t in tok], 1)   # (900, n_ifade)
    sonuc = []
    for q in np.where(olas.max(axis=1) > kutu_esik)[0]:
        j = int(ifade_ol[q].argmax())
        if ifade_ol[q, j] <= yazi_esik:
            continue
        cx, cy, w, h = kut[q]
        sonuc.append(dict(x0=float(max(0, (cx - w / 2) * gn)), y0=float(max(0, (cy - h / 2) * yk)),
                          x1=float(min(gn, (cx + w / 2) * gn)), y1=float(min(yk, (cy + h / 2) * yk)),
                          skor=float(ifade_ol[q, j]), ifade=ifadeler[j]))
    return sonuc


# ---- oyun ekrani kurallari (bot.py ile ayni kural, sade kopya) ----

def arayuz_maskesi(yuk, gen):
    """Oyun alani disinda kalan (arayuz) bolgeler: True = yok say."""
    m = np.zeros((yuk, gen), bool)
    m[:210, gen - 190:] = True          # mini harita
    m[yuk - 55:, :] = True              # alt cubuk
    m[yuk - 135:, 580:1340] = True      # sohbet satirlari
    m[:45, :200] = True                 # sol ust etki simgeleri
    m[225:350, gen - 235:] = True       # sagdaki etkinlik simgesi (kirmizi gul vb.)
    m[:70, gen // 2 - 260:gen // 2 + 260] = True    # hedef penceresi
    return m


def beyaz_etiketler(kare):
    """Beyaz isim yazilari (solunda yesil 'Lv N'): metin taslari (ve bazi oyuncular). [(x_orta, y_alt, gen, yuk)]"""
    r, g, b = cv2.split(kare)                                    # cv2 ile (bot.py'deki int kopya ~0.3 sn suruyordu)
    mx, mn = cv2.max(cv2.max(r, g), b), cv2.min(cv2.min(r, g), b)
    maske = (mn > 175) & (cv2.subtract(mx, mn) < 45)
    maske &= ~arayuz_maskesi(*kare.shape[:2])
    m8 = cv2.dilate(maske.astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_RECT, (11, 3)))
    n, _, ist, _ = cv2.connectedComponentsWithStats(m8, 8)
    sonuc = []
    for i in range(1, n):
        x, y, w, hh, _ = ist[i]
        if 22 <= w <= 200 and 8 <= hh <= 20:
            dolu = maske[y:y + hh, x:x + w].sum()
            if dolu >= 20 and dolu / (w * hh) < 0.55:
                sol = kare[y:y + hh, max(0, x - 50):x].astype(int)
                yesil = ((sol[..., 1] > 140) & (sol[..., 0] < 170) & (sol[..., 2] < 100)).sum()
                if yesil >= 8:
                    sonuc.append((x + w // 2, y + hh, w, hh))
    return sonuc


_kapat = []


def pencere_bolgeleri(kare):
    """Acik oyun pencereleri (envanter, arkadas listesi...): kizil baslikli kapatma dugmesinden sola/asagi bolge."""
    if not _kapat:
        _kapat.append(cv2.imread(os.path.join(KLASOR, "sablon", "kapat.png"), 0))
    s = _kapat[0]
    if s is None:
        return []
    yk, gn = kare.shape[:2]
    r = cv2.matchTemplate(cv2.cvtColor(kare, cv2.COLOR_RGB2GRAY), s, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(r >= 0.85)
    bolge, gorulen = [], []
    for x, y in zip(xs, ys):
        cx, cy = int(x) + s.shape[1] // 2, int(y) + s.shape[0] // 2
        if cx < 70 or (cy < 75 and abs(cx - gn // 2) < 320) or any(abs(cx - a) < 6 and abs(cy - b) < 6 for a, b in gorulen):
            continue
        gorulen.append((cx, cy))
        sol = kare[max(0, cy - 4):cy + 5, cx - 60:cx - 25].reshape(-1, 3).mean(axis=0)
        if not (sol[0] > 85 and sol[0] > 1.6 * sol[1]):                # kizil baslik cubugu yok: pencere degil
            continue
        satir = kare[cy, :cx].astype(int)
        kizil = (satir[:, 0] > 60) & (satir[:, 0] > 1.5 * satir[:, 1])
        sol_x, bosluk = cx - 25, 0
        for xx in range(cx - 25, max(0, cx - 900), -1):                # baslik cubugunun sol ucu
            if kizil[xx]:
                sol_x, bosluk = xx, 0
            else:
                bosluk += 1
                if bosluk > 70:
                    break
        bolge.append((max(0, sol_x - 45), max(0, cy - 15), min(gn, cx + 15), yk - 55))
    return bolge


def kendi_karakter_mi(b, yk, gn):
    """Kamera karakteri ortalar (ad etiketi y~0.42-0.47*yk, govde altinda).
    1) ekran ortasi (x=gn/2, y~0.51*yk) noktasini iceren, tepesi 0.40*yk'nin altinda orta boy kutu = biz
       (tepesi daha yukarida olan: karakterin ustune binen yaratik, orn. 134934 kopek);
    2) merkezi ortanin +-60 px / 0.47-0.55*yk icinde kalan kucuk 'person' kutusu = karakterin parcasi
       (101428'de x=926). Yalniz 'person': dibimizdeki hayvan korunur (082438 beyaz kurt); bedeli,
       karakterin hemen yanindaki insansi yaratik da silinir (102345, x=994)."""
    x0, y0, x1, y1 = _k(b)
    if x0 < gn / 2 < x1 and y0 < 0.51 * yk < y1 and y0 > 0.40 * yk and (x1 - x0) < 450:
        return True
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return (b.get("ifade") == "person" and abs(cx - gn / 2) < 60 and 0.47 * yk < cy < 0.55 * yk
            and (x1 - x0) < 160 and (y1 - y0) < 200)


def suz(ham, rgb, nms=None):
    """Arayuz, acik pencere, kendi karakterimiz, dev kutular, cakisanlar (sinif bagimsiz NMS) ve
    birden cok nesneyi kapsayan grup kutulari atilir."""
    yk, gn = rgb.shape[:2]
    nms = NMS_ESIK if nms is None else nms
    maske = arayuz_maskesi(yk, gn)
    pen = pencere_bolgeleri(rgb)
    aday = []
    for b in sorted(ham, key=lambda d: -d["skor"]):
        x0, y0, x1, y1 = _k(b)
        w, h = x1 - x0, y1 - y0
        cx, cy = int(min(gn - 1, (x0 + x1) / 2)), int(min(yk - 1, (y0 + y1) / 2))
        if w < 10 or h < 10 or w * h > 0.25 * gn * yk or maske[cy, cx]:
            continue
        if any(p[0] <= cx <= p[2] and p[1] <= cy <= p[3] for p in pen):
            continue
        if kendi_karakter_mi(b, yk, gn):
            continue
        if any(_iou(_k(b), _k(c)) > nms for c in aday):
            continue
        aday.append(b)
    sonuc = []
    for b in aday:                                                # grup kutusu: >=2 kutuyu %80+ iceriyor
        icerik = sum(1 for c in aday if c is not b and _icinde(_k(c), _k(b)) > 0.8)
        if icerik < 2:
            sonuc.append(dict(b, grup=b.get("grup") or IFADELER.get(b["ifade"], "?")))
    return sonuc


def tas_kutulari(rgb):
    """Beyaz adli etiketin (Lv + ad) altindaki kirpintida tek ifadeli tas aramasi."""
    yk, gn = rgb.shape[:2]
    sonuc = []
    for x, ya, _, _ in beyaz_etiketler(rgb):
        if abs(x - gn / 2) < 120 and 0.38 * yk < ya < 0.5 * yk:
            continue                                              # kendi ad etiketimiz
        x0, y0, x1, y1 = max(0, x - 200), max(0, ya - 20), min(gn, x + 200), min(yk - 55, ya + 300)
        if x1 - x0 < 60 or y1 - y0 < 60:
            continue
        h = ham_kutular(np.ascontiguousarray(rgb[y0:y1, x0:x1]), ifadeler=[TAS_IFADE], kutu_esik=TAS_ESIK, yazi_esik=TAS_ESIK)
        h = [dict(b, x0=float(b["x0"] + x0), x1=float(b["x1"] + x0), y0=float(b["y0"] + y0), y1=float(b["y1"] + y0),
                  grup="metin") for b in h]
        h = [b for b in h if abs((b["x0"] + b["x1"]) / 2 - x) < 70 and 0 < b["y0"] - ya < 130]
        if h:
            en = max(h, key=lambda b: b["skor"])
            if not any(_iou(_k(en), _k(c)) > 0.5 for c in sonuc):
                sonuc.append(en)
    return sonuc


def kutular(rgb, tezgah=False):
    """Bir oyun karesi icin suzulmus DINO kutulari: [dict(x0,y0,x1,y1,skor,ifade,grup)]"""
    ana = suz(ham_kutular(rgb), rgb)
    tas = tas_kutulari(rgb)
    ana = [b for b in ana if not any(_iou(_k(b), _k(t)) > 0.3 for t in tas)]   # ana gecis tasi 'animal' sanir
    ek = []
    if tezgah:
        ek = suz([dict(b, grup="pazar") for b in ham_kutular(rgb, ifadeler=[TEZGAH_IFADE], kutu_esik=TEZGAH_ESIK,
                                                              yazi_esik=TEZGAH_ESIK)], rgb)
        ana = [b for b in ana if not any(_iou(_k(b), _k(t)) > 0.5 for t in ek)]
    return ana + tas + ek


RENK = {"yaratik": (255, 60, 60), "insan": (60, 200, 255), "metin": (255, 255, 255), "pazar": (255, 200, 0), "?": (255, 0, 255)}


def ciz(rgb, kut):
    c = rgb.copy()
    for b in kut:
        r = RENK.get(b.get("grup", "?"), (255, 0, 255))
        cv2.rectangle(c, (int(b["x0"]), int(b["y0"])), (int(b["x1"]), int(b["y1"])), r, 2)
        cv2.putText(c, f'{b["ifade"]} {b["skor"]:.2f}', (int(b["x0"]), max(12, int(b["y0"]) - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, r, 1, cv2.LINE_AA)
    return c


if __name__ == "__main__":
    yol = [a for a in sys.argv[1:] if not a.startswith("--")]
    k = cv2.cvtColor(cv2.imread(yol[0]), cv2.COLOR_BGR2RGB)
    _yukle()
    t = time.time()
    kt = kutular(k, tezgah="--tezgah" in sys.argv)
    print(f"{len(kt)} kutu, {time.time() - t:.2f} sn")
    for b in kt:
        print({a: (round(v, 1) if isinstance(v, float) else v) for a, v in b.items()})
    if len(yol) > 1:
        cv2.imwrite(yol[1], cv2.cvtColor(ciz(k, kt), cv2.COLOR_RGB2BGR))
