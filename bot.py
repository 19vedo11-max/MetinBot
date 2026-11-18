"""MetinBot - Waryong2 icin ekran okuyan kasilma botu.

Calistirma (YONETICI olarak, oyun yonetici yetkisiyle calistigi icin):
    python bot.py            -> kasilma dongusu
    python bot.py --kuru     -> tus/fare gondermez, bir kare alip tespiti goruntu/tespit.png'ye cizer
    python bot.py --dosya goruntu/ekran2.png  -> kayitli goruntude tespit dener

Tuslar:  F10 = duraklat/devam   F12 = kapat
Bot yalniz oyun penceresi ondeyken girdi gonderir; baska pencereye gecersen bekler.
"""
import ctypes
import difflib
import json
import math
import os
import random
import re
import sys
import threading
import time

import cv2
import numpy as np
import win32gui
from PIL import Image, ImageGrab

import gorev_yurut as gy_mod
import oku
import rakam
import yol as yolbul

ctypes.windll.user32.SetProcessDPIAware()
KLASOR = os.path.dirname(os.path.abspath(__file__))

VARSAYILAN = {
    "pencere_basligi": "Waryong2",
    "mod": "slot",                # "slot" = yaratik kes, "metin" = yalniz metin tasi, "ikisi" = once metin sonra yaratik
    "saldiri_tusu": "space",
    "toplama_tusu": "z",
    "esyaya_tikla": True,         # yerdeki esya/yang etiketine tiklayarak topla
    "esya_yaricapi_piksel": 650,
    "en_cok_esya": 10,            # bir toplama turunda en cok kac esyaya tiklansin
    "alan_bos_sn": 10,            # alan modunda bu kadar sn slot kesilmezse kisa yuruyusleri beklemeden alana don
    "alana_donerken_dal": True,   # alana donerken yolda slot gorurse yuruyusu kesip ona dal
    "dalinca_hemen_sn": 10,       # yolda slota dalinca bu kadar sn yan isleri atla, dogrudan vur
    "guc_on_mesafe": 350,         # slottan once guclendirme yalniz ilk hedef bundan uzaksa (yaklasana kadar yakilir)
    "derinlik_sirala": True,      # hedefleri ekran uzakligi yerine kamera derinligine gore (gercek yakinlik) sirala
    "derinlik_ufuk": 227,         # derinlik modeli: govde boyu ~ (y + ufuk)
    "derinlik_carpan": 1.7,       # karakter yaninda dikey 1 px ~ bu kadar yatay px yol
    "grup_sonu_guc": True,        # grup bitince bekleme suresi dolan hava kilici/ofke'yi hemen yak
    "yakin_saldir": True,         # dibime gelen yaratiga (seviye/ad filtresine bakmadan) canim dusmeden hemen vur
    "yakin_saldir_piksel": 190,   # 'dibimde' sayilan uzaklik (karakter merkezinden)
    "ince_vurus": True,           # 1 piksellik can dususunu de vurus say; menzil disindaki hedefe bosa sallamadan yaklas
    "grup_hasarsiz_sn": 15,       # grupta kalirken bu kadar sn hic can dusuremediyse (yokus/duvar) kalma, yer degistir
    "grupta_kal": True,           # slotta ulasilamayan/vurulamayan yaratik olursa, etrafta canli varken kacma: atla, digerlerine vur
    "hizli_vazgec": True,         # ulasilamayan hedefte bekleme kisalt + atla suresini uzat
    "hizli_vazgec_atla_sn": 45,   # ulasilamayan hedef (ayni nokta) bu kadar sn secilmez (eski: 12)
    "gorev_av_okuma_sn": 900,     # yalniz av gorevi icin gorev listesini bu aralikla oku (0 = npc_gorev_araligi_sn)
    "ilk_vurus_bekleme_sn": 7,    # hedefe tikladiktan sonra ilk vurus icin en cok bu kadar bekle
    "takilma_sn": 1.2, 
    "takilma_esik": 1.2,          # mini harita 1 sn icinde bundan az degisirse karakter yerinde sayiyor           # sahne bu kadar sure hic degismezse karakter engele takilmis sayilir
    "hizli_engel": False,          # savas disi yuruyuste 0.8 sn kipirdamazsa beklemeden bos yone 1 adim yan cik
    "su_kacin": True,             # ekranda nehir/gol (mavi-turkuaz zemin) varsa o yone tiklama
    "engel_hafiza": True,         # takildigi yeri engeller.json'a yaz; alan/gezin noktasi secerken oralardan kac
    "durgun_esik": 1.0,           # iki kare arasi ortalama fark bunun altindaysa "duruyor"
    "kamera_donus_sn": 0.6,       # hedef yokken kamerayi her adimda bu kadar sure dondur
    "can_potu_tusu": "1",
    "can_esigi": 0.5,             # can bu oranin altina inince pot bas
    "mana_potu_tusu": "2",        # bos birakirsan ("") mana potu basmaz
    "mana_esigi": 0.3,
    "sureli_tuslar": [{"tus": "3", "aralik_sn": 55}, {"tus": "f3", "aralik_sn": 55}],  # hava kilici, ofke (sure tahmini)
    "envanter_kullan": [          # envanterde simgesi bulunup sag tiklananlar
        {"sablon": "yesil_iksir.png", "aralik_sn": 180},   # hareket hizi
        {"sablon": "mor_iksir.png", "aralik_sn": 180},     # saldiri hizi
        {"sablon": "sandik.png", "aralik_sn": 900},        # seviye sandigi
    ],
    "sadece_slot": True,          # yalniz grup halindeki yaratiklara (slot) git
    "slot_en_az": 3,              # bir grubun slot sayilmasi icin en az yaratik sayisi
    "slot_yaricapi_piksel": 200,  # bu mesafedeki yaratiklar ayni grup sayilir
    "tekli_bekleme_turu": 10,     # bu kadar tur slot cikmazsa tek yaratiklara da izin ver
    "toplanacak_grup": 3,         # kesmeden once kac gruba birer vurus atilsin (1 = toplama kapali)
    "grup_ayrim_piksel": 230,     # bu mesafeden uzaktaki yaratik "baska grup" sayilir
    "toplama_can_siniri": 0.6,    # can bunun altindaysa toplamayi birakip kesmeye gec
    "spot_ust_sure_sn": 120,
    "sinif": "savasci",           # savasci / ninja / sura / saman (siniflar.py hazir ayarlari; panel bilgisi)
    "uzak_dovus": False,          # okcu, kara buyu, saman: tiklayinca karakter menzile kadar kendi yaklasir (hamle kapali olmali)
    "statu": "str",               # statu puani hangi ozellige: vit / int / str / dex ("" = dagitma)
    "karakter_tusu": "c",
    "beceri_grubu": "bedensel",   # egitmene gidip secilecek grup ("" = egitmene gitme)
    "egitmen_anahtar": "bedensel",# haritadaki NPC adinda aranacak kelime
    "saldiri_becerileri": [       # slot keserken kullanilan beceriler (sure tahmini)
        {"tus": "4", "aralik_sn": 6}, {"tus": "f1", "aralik_sn": 6}, {"tus": "f2", "aralik_sn": 6}],
    "olunce_yeniden_basla": True,
    "yeniden_baglan": True,       # oyundan atilinca giris ekraninda kayitli hesapla (F1) yeniden baglan
    "olum_sehir_sayisi": 2,       # bu kadar olum ...
    "olum_sehir_pencere_sn": 120, # ... bu sure icinde olursa sehirde yeniden basla (dusmanlarin arasinda dirilme)
    "saldiran_yaricapi_piksel": 190,  # karakterin bu kadar yakinindaki yaratik (saldiran) slot sartsiz once kesilir
    "npc_adlari": {"biyolog": ["biyolog", "chaeg", "hagair", "olog", "egirab"], "olay yard": ["olay", "yardimci", "ji-min"],
                   "bedensel": ["bedensel", "savas ogret"]},
    "yolda_saldiri_can": 0.7,     # NPC'ye ya da baska bolgeye yururken can bunun altina inerse yolculugu birak
    "npc_gorevleri": True,        # gorev listesinde adi gecen NPC'ye gidip konus
    "npc_gorev_araligi_sn": 300,
    "gorev_metni_topla": True,    # gorev aciklama metinlerini gorev_metinleri.json'a topla (yalniz okur, ilerletmez)
    "halkali_npc": False,         # haritadaki pembe halkali yerlere gitme (Vedat istemedi; cogu yarim gorev, bosa yuruyus)
    "npc_tekrar_dk": 20,          # ayni NPC'ye en erken bu kadar dakika sonra yeniden git
    "gorev_npcleri": {            # gorev yazisinda gecen kelime -> haritadaki NPC adi
        "biyolog": "biyolog", "chaegirab": "biyolog", "ji-min": "olay yard", "olay yard": "olay yard",
        "yuzbasi": "yuzbasi", "depocu": "depocu", "balikci": "balikci", "gardiyan": "gardiyan"},
    "guclendirme_en_az_aralik_sn": 30,   # sonen guclendirmeyi yeniden yakmayi en erken bu kadar sonra dene
    "beceri_puani_dagit": True,
    "oncelikli_beceri_konumu": [-123, 138],   # eski tek oncelik (artik beceri_sirasi kullaniliyor)
    "beceri_sirasi": ["hava_kilici", "ofke", "uc_yonlu", "kilic_cevirme", "hamle"],  # bastaki master olunca siradaki
    "beceri_birer_ver": False,    # ilk seferde her beceriye 1 puan verme (eski davranis)
    "beceri_sira_konum": [],      # panelde tiklanan beceri ikonlari (kapat dugmesine gore); bossa beceri_sirasi
    "gorev_araligi_sn": 30,      # bu aralikla sol kenardaki gorev parsomenlerinden birine tiklar (0 = kapali)
    "izleme_araligi_sn": 40,     # bu aralikla goruntu/izleme klasorune kare kaydeder
    "spot_yaricapi_piksel": 240,  # olen hedefin ardindan bu yaricaptaki yaratiklara ara vermeden gec
    "envanter_tusu": "i",
    "beceri_tuslari": [],     # ornek: ["f1", "f2"]
    "beceri_araligi_sn": 20,
    "hedef_basi_ust_sure_sn": 30, # bir yaratikla en fazla bu kadar ugras
    "vuramama_siniri_sn": 7,      # hedefin cani bu kadar sure dusmezse baska hedefe gec
    "yakinlik_halkasi_piksel": 260,  # bu mesafe icindeki slotlar "yakin" sayilir; yakindakiler once, icinde yuksek seviye
    "gorev_tusu": "n",            # gorev penceresini acan tus
    "seviye_alt_fark": 3,         # kendi seviyenden en cok bu kadar dusuk yaratik "exp veren" sayilir
    "toplama_en_uzak_piksel": 450,   # grup toplarken ekranda bundan uzaktaki gruba gitme
    "yurumeden_once_tur": 8,      # hedef yokken yurumeden once kac adim kamera cevrilsin
    "seviye_kontrol_dk": 10,      # C penceresi bu aralikla okunur (seviye + saatlik tecrube olcumu)
    "alan_donus_sn": 900,          # alan modunda slot bitince en erken bu araliklarla alanin icine geri yuru
    "dalma_olum_sayisi": 4,       # bu kadar olum ...
    "dalma_olum_sn": 60,          # ... bu sure icinde olursa ...
    "dalma_yok_dk": 10,           # ... bu kadar dakika kalabalik slotlara dalma (tek/ikili yaratik kes)
    "dirilince_kalabalik": 4,     # dirildigim yerde bu kadar yaratik varsa once uzaklas
    "gezin_bekle_sn": 12,         # gezinme yuruyusu baslayinca bu sure yeniden harita acma (yuruyus bolunmesin)
    "dusuk_izin_sn": 240,         # yalniz dusuk seviyeli varken bu sure onlari da kes
    "hamle_tusu": "f2",           # uzaktaki hedefe atilma becerisi (bedensel: Hamle); bos = kapali
    "hamle_min_piksel": 260,      # hedef bundan uzaksa hamle ile git
    "hamle_aralik_sn": 8,
    "savunma_can_esigi": 0.9,     # can bunun altindayken yanimda yaratik varsa hemen ona don
    "savunma_yaricapi_piksel": 330,   # hasar alinca bu yaricaptaki her yaratik hedef (seviye/slot filtresi yok)
    "yolo_veri_sn": 4,            # sekil modeli egitim verisi: bu aralikla kare kaydet (0 = kapali)
    "yolo_veri_en_cok": 3000,
    "kare_paylas_klasoru": "",    # bos = kapali; doluysa kaydedilen karelerin bir kismi bu klasore kopyalanir
    "kare_paylas_adi": "",        # paylasanin takma adi (bos = bilgisayar adi)
    "kare_paylas_gunluk": 200,    # gunde en cok bu kadar kare paylas
    "alan_kullan": False,         # True: cizilen kasilma alaninin disina cikma (panelde secenek)
    "gorev_yurutucu": True,       # gorev_tablosu.json sirasiyla gorevleri yurut (yalniz profil yalniz_gorev/gorev)
    "gorev_esya_dk": 5,           # esya_dusur adiminda yaratigi bu kadar dk kes, sonra NPC'ye teslime git
    "yalniz_gorev": False,        # True: genel slot kesme yok; yalniz gorev yaratigi, NPC ve parsomen
    "kasilma_alani": None,        # panelde haritaya cizilen daire {"harita", "x", "y", "r"} (oran); doluysa bot disina cikmaz
    "olum_dongusu_sayisi": 3,     # bu kadar olum ...
    "olum_dongusu_sn": 180,       # ... bu sure icinde olursa sehirde dirilip koyden disari yuru
    "temkin_dk": 20,              # 2 olumden sonra bu kadar dakika ...
    "temkin_ust_fark": 2,         # ... en cok (seviye + bu) yaratiklara saldir      # seviye C (karakter) penceresinden bu aralikla okunur
    "seviye_ust_fark": 3,         # kendi seviyenden en cok bu kadar yuksek yaratiga saldir
    "en_fazla_yaratik_seviyesi": 9,  # yalniz kendi seviyen okunamazsa kullanilir
    "metin_vurus_suresi_sn": 120,
    "metin_kes": True,            # ekrandaki metin taslarini (adini okuyarak) slottan once kes
    "metin_tarama_sn": 3,
    "metin_kelimeleri": ["metin", "metni", "tasi", "metini"],  # metin tasi icin ust sinir
    "etiket_alti_piksel": 45,     # isim yazisinin kac piksel altina tiklansin
    "kamera_tusu": "e",           # hedef yokken kamerayi dondurur
    "kamera_egim_t_sn": 0.55,     # G ile tepeye dikip T'ye bu kadar basili tut (yatay aci); 0 = kameraya dokunma
    "kamera_egim_aralik_sn": 180,
    "kamera_uzak_tusu": "",       # bos: kameraya dokunma (F bu sunucuda kamerayi tepeye dikiyordu)      # kamerayi uzaklastirir (Metin2: R yakin, F uzak)
    "kamera_uzak_aralik_sn": 30,  # bu aralikla kamerayi en uzaga al (genis gorus, slotlar ekranda)
    "gezinme_turu": 14,           # bu kadar tur hedef bulunamazsa haritadan baska bolgeye yuru (bot durmaz)
    "gezinme_en_uzun_sn": 45,
    "aranan_yaratiklar": [],      # gorevin istedigi yaratik adlari (elle); gorev yazisindan okunanlar durum.json'da
    "aranan_tarama_sn": 5,        # yaratik adlari en sik bu aralikla okunur
    "etrafa_bakma_sn": 2.5,       # hedef kalmayinca kamera surekli donerken en cok bu kadar bakilir, sonra baska bolge
    "toplama_en_uzun_sn": 2.0,    # slot sonrasi yerdeki esyalari toplamaya en cok bu kadar sure
    "aranan_oncelik": True,       # gorev yazisinda adi gecen yaratigi (or. cicek dusuren kurt) one al
    "av_gorevi": True,            # av gorevinin istedigi yaratigi one al (kasilirken av gorevi de biter)
    "gorev_parsomen": True,       # sol kenardaki gorev parsomenlerini ac (odul al, yeni av gorevi sec)
    "dusuk_seviye_kesme": True,   # seviyemden cok dusuk yaratigi kesme; cevrede yalniz onlar varsa uygun bolgeye git
    "esya_avi": "",               # esya_avi.json'dan secilen esya adi: dustugu canavarlar one alinir
    "imparatorluk": "jinno",      # koy bayragi menusunde secilecek imparatorluk (mavi bayrak = Jinno)
    "koyler": ["pyungmoo", "bakra"],  # bayragin 2. adimindaki 1. ve 2. koy
    "profil": "ozel",             # level / gorev / metin / ozel (panelden secilir; ozel = asagidaki ayarlar aynen)
    "sadece_toplama": False,      # True: bot yalniz toplama tusuna basar (oyuncu kendisi oynuyor)
    "toplama_araligi_sn": 0.25,
    "grup_en_az": 3,              # bir grupta en az bu kadar canavar olmeden slot bitmis sayilmaz
    "guc_can_esigi": 0.5,         # can bunun altindayken hava kilici / ofke (sureli_tuslar) basilmaz
    "mini_harita_yuru": True,     # buyuk haritadan once mini haritadaki kirmizi nokta kumesine yuru
    "alan_kisa_yuruyus": 5,      # slot bitince haritasiz kisa yuruyusle ayni alanda kac kez aransin
    "dolum_esigi": 0.85,          # grup bitince can bu orana kadar pot ile doldurulur
    "yolo_gpu": True,            # sekil modeli ekran kartinda ayri surecte (sekil_sunucu.py); yoksa CPU
    "yolo_kullan": True,         # sekil modeli (sekil.py) yardimci: etiketsiz yaratik + oyuncu korumasi
    "yolo_esik": 0.45,           # yaratik kutusu min skoru
    "yolo_slot": True,           # slot icinde etiket yoksa YOLO yaratik kutusuna vur
    "yolo_oyuncu_koru": True,    # etiketin govdesi YOLO oyuncu ise hedef alma
    "sadece_hedefler": [],        # doluysa yalniz adi bunlara tutan canavarlar kesilir (or. "Kotu Siyah Firtina Okcusu")
    "pot_satin_al": True,         # can potu bitince koydeki Saticidan al (20'lik kucuk iksir paketleri)
    "pot_al_kirmizi_paket": 5,    # kac paket kucuk kirmizi (her biri 20 adet)
    "pot_al_mavi_paket": 1,       # kac paket kucuk mavi
    "pot_yuvasi_doldur": False,    # 1/2 pot yuvasi bosalinca envanterden doldur (denemede yerlesmedi - kapali)
    "bos_tur_siniri": 40,         # bu kadar tur ust uste hedef yoksa dur
    "olum_kare_siniri": 5,        # can bu kadar kare ust uste sifirsa dur
}


# Yetenekler sekmesinde becerilerin ARTI dugmesi konumu (kapat dugmesine gore; 16.11 ekran goruntusunden olculdu)
BECERI_KONUM = {"uc_yonlu": (-263, 93), "kilic_cevirme": (-123, 93), "ofke": (-263, 138),
                "hava_kilici": (-123, 138), "hamle": (-263, 183)}

# Gunluk plan: secilen profil, ayar.json'daki degerlerin USTUNE yazilir ("ozel" hicbir seye dokunmaz).
PROFILLER = {
    # ana is: level ve metin yalniz metin tasina bakar; gorevle ilgili dort ayar (av gorevi, gorev yaratigi,
    # NPC gorevleri, parsomenler) panelden ayri ayri secilir. "gorev" = hepsi acik, NPC'lere sik gidilir.
    "toplama": {"sadece_toplama": True},
    "level": {"metin_kes": False},
    "metin": {"metin_kes": True},
    "gorev": {"metin_kes": False, "npc_gorevleri": True, "aranan_oncelik": True, "av_gorevi": True,
              "gorev_parsomen": True, "npc_gorev_araligi_sn": 150, "gorev_araligi_sn": 30},
    "yalniz_gorev": {"metin_kes": False, "npc_gorevleri": True, "aranan_oncelik": True, "av_gorevi": True,
                     "gorev_parsomen": True, "npc_gorev_araligi_sn": 90, "gorev_araligi_sn": 30,
                     "yalniz_gorev": True, "halkali_npc": True, "sadece_hedefler": ["(gorev yaratigi yok)"]},
    "ozel": {},
}


_PAYLAS = {"n": 0, "gun": "", "say": 0}


def _kare_paylas(kare, ayar):
    """Kaydedilen her 5. kareyi paylasim klasorune kopyalar (kapaliysa/hatada sessizce gecer)."""
    try:
        kl = (ayar.get("kare_paylas_klasoru") or "").strip()
        if not kl or not os.path.isdir(kl):
            return
        _PAYLAS["n"] += 1
        if _PAYLAS["n"] % 5:
            return
        gun = time.strftime("%Y%m%d")
        if _PAYLAS["gun"] != gun:
            _PAYLAS["gun"], _PAYLAS["say"] = gun, 0
        if _PAYLAS["say"] >= int(ayar.get("kare_paylas_gunluk") or 0):
            return
        ad = re.sub(r'[\\/:*?"<>|]+', "_", (ayar.get("kare_paylas_adi") or "").strip()
                    or os.environ.get("COMPUTERNAME", "bilgisayar"))
        hk = os.path.join(kl, ad, gun)
        os.makedirs(hk, exist_ok=True)
        Image.fromarray(kare).save(os.path.join(hk, time.strftime("%H%M%S") + ".jpg"), quality=85)
        _PAYLAS["say"] += 1
    except Exception:
        pass




def ayar_yukle():
    yol = os.path.join(KLASOR, "ayar.json")
    ayar = dict(VARSAYILAN)
    if os.path.exists(yol):
        with open(yol, encoding="utf-8-sig") as f:
            ayar.update(json.load(f))
    else:
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(VARSAYILAN, f, ensure_ascii=False, indent=2)
    ayar.update(PROFILLER.get(ayar.get("profil"), {}))
    return ayar


# ---------------------------------------------------------------- pencere
def pencere_bul(baslik):
    bulunan = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h) and baslik in win32gui.GetWindowText(h) \
                and win32gui.GetClassName(h).startswith("eter"):
            bulunan.append(h)

    win32gui.EnumWindows(cb, None)
    return bulunan[0] if bulunan else None


def istemci_kutusu(h):
    x, y = win32gui.ClientToScreen(h, (0, 0))
    _, _, w, hh = win32gui.GetClientRect(h)
    return x, y, w, hh


_mss_yerel = threading.local()


_dx = {"kam": None, "bolge": None, "hata": False, "kilit": threading.Lock()}


def _dx_kare(x, y, w, hh):
    """DXGI ile surekli yakalama (dxcam): en yeni kare ~16 ms (mss 33 ms). Olmazsa None."""
    if _dx["hata"]:
        return None
    try:
        import dxcam
        bolge = (max(0, x), max(0, y), x + w, y + hh)
        with _dx["kilit"]:
            if _dx["kam"] is None:
                _dx["kam"] = dxcam.create(output_color="RGB")
            kam = _dx["kam"]
            bolge = (bolge[0], bolge[1], min(kam.width, bolge[2]), min(kam.height, bolge[3]))
            if _dx["bolge"] != bolge:
                if _dx["bolge"] is not None:
                    kam.stop()
                kam.start(region=bolge, target_fps=60, video_mode=True)
                _dx["bolge"] = bolge
        f = kam.get_latest_frame()
        if f is None:
            return None
        if f.shape[0] != hh or f.shape[1] != w:              # pencere ekran kenarindan tasiyorsa eksik kenari doldur
            t = np.zeros((hh, w, 3), np.uint8)
            t[:f.shape[0], :f.shape[1]] = f[:hh, :w]
            return t
        return f
    except Exception as e:
        print("dxcam kullanilamiyor, mss ile devam:", e)
        _dx["hata"] = True
        return None


_son_kare = [None]


def dunya_uzak(x, y, kx, ky, ufuk=227.0, carpan=1.7):
    """Ekran noktasinin karaktere 'dunyada' uzakligi (karakter derinliginde piksel birimi). Kamera egik oldugu
    icin ekranda yukaridaki (uzaktaki) yaratigin 1 pikseli yandakinden cok daha fazla yol demek:
    derinlik ~ 1/(y + ufuk) (otomatik etiketlerde govde boyu = 0.11*(y+227)'den), dikey 1 px ~ carpan yatay px."""
    d = (ky + ufuk) / max(30.0, y + ufuk)
    return math.hypot((x - kx) * d, carpan * (ky + ufuk) * (d - 1.0))

_ZAMAN_YOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zamanlar.json")


def zaman_oku(ad, varsayilan=0.0):
    """Bot yeniden acilsa da korunan zamanlar (gorev okuma vb.): her acilista bastan yapilmasin."""
    try:
        with open(_ZAMAN_YOL, encoding="utf-8") as f:
            return float(json.load(f).get(ad, varsayilan))
    except Exception:
        return varsayilan


def zaman_yaz(ad, deger):
    try:
        try:
            with open(_ZAMAN_YOL, encoding="utf-8") as f:
                z = json.load(f)
        except Exception:
            z = {}
        z[ad] = deger
        with open(_ZAMAN_YOL, "w", encoding="utf-8") as f:
            json.dump(z, f)
    except Exception:
        pass


_yolo = {"t": 0.0, "kutular": [], "kare_t": 0.0, "ms": 0.0, "sag": None, "ayar": {}}   # sekil izleginin paylasilan durumu


def yolo_taze(yas=1.2):
    """Son YOLO tespitleri (yas sn icindeyse), yoksa []. CPU'da bir cikarim ~0.4 sn: pencere 1.2 sn."""
    return _yolo["kutular"] if time.time() - _yolo["t"] <= yas else []


def _kesisim(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def yolo_oyuncu_etiketi_mi(x, y):
    """(x, y) kirmizi etiketin govdesi (x+-60, y+10..+200) YOLO'da oyuncuya ait, yaratiga degil mi?"""
    if not _yolo["ayar"].get("yolo_oyuncu_koru", True) or not _yolo["ayar"].get("yolo_kullan", True):
        return False
    kutular = yolo_taze()
    if not kutular:
        return False
    bolge = (x - 60, y + 10, x + 60, y + 200)
    alan = 120 * 190.0
    oy = any(k[0] == "oyuncu" and k[1] >= 0.5 and _kesisim(bolge, k[2:]) > 0.15 * alan for k in kutular)
    if not oy:
        return False
    return not any(k[0] == "yaratik" and _kesisim(bolge, k[2:]) > 0.10 * alan for k in kutular)


def yolo_yaratik_yakin(gen, yuk, yaricap):
    """Karakter merkezine yaricap icindeki en yakin YOLO yaratik kutusu: (cx, govde_ortasi_y) ya da None."""
    if not _yolo["ayar"].get("yolo_kullan", True) or not _yolo["ayar"].get("yolo_slot", True):
        return None
    kx, ky = gen // 2, yuk * 0.58
    en = None
    for k in yolo_taze():
        if k[0] != "yaratik" or k[1] < _yolo["ayar"].get("yolo_esik", 0.45):
            continue
        cx, cy = (k[2] + k[4]) / 2, (k[3] + k[5]) / 2
        d = math.hypot(cx - kx, cy - ky)
        if d < yaricap and (en is None or d < en[0]):
            en = (d, cx, cy)
    return (en[1], en[2]) if en else None


def kare_al(h):
    """Oyun penceresinin karesi. Pencere kucultulmus / ekran disina tasmis / bos kare gelirse cokme yerine
    bekleyip yeniden dener; olmazsa son iyi kareyi (yoksa siyah kare) dondurur."""
    for _d in range(6):
        try:
            f = _kare_al_ic(h)
            if f is not None and f.size and f.shape[0] > 100 and f.shape[1] > 100:
                _son_kare[0] = f
                _yolo["kare_t"] = time.time()
                return f
        except Exception:
            pass
        time.sleep(0.5)
    return _son_kare[0] if _son_kare[0] is not None else np.zeros((1111, 1920, 3), np.uint8)


def _kare_al_ic(h):
    if win32gui.IsIconic(h):                       # oyun simge durumuna kucultulmus: geri ac (yoksa bos kare -> cokus)
        win32gui.ShowWindow(h, 9)
        time.sleep(1.0)
    x, y, w, hh = istemci_kutusu(h)
    f = _dx_kare(x, y, w, hh)
    if f is not None:
        return f
    try:
        import mss
        if not hasattr(_mss_yerel, "s"):
            _mss_yerel.s = mss.MSS() if hasattr(mss, "MSS") else mss.mss()
        ham = np.asarray(_mss_yerel.s.grab({"left": x, "top": y, "width": w, "height": hh}))
        return cv2.cvtColor(ham, cv2.COLOR_BGRA2RGB)
    except Exception:
        return np.array(ImageGrab.grab(bbox=(x, y, x + w, y + hh)).convert("RGB"))


# ---------------------------------------------------------------- tespit
def arayuz_maskesi(yuk, gen):
    """Oyun alani disinda kalan (arayuz) bolgeler: True = yok say."""
    m = np.zeros((yuk, gen), bool)
    m[:210, gen - 190:] = True          # mini harita
    m[yuk - 55:, :] = True              # alt cubuk
    m[yuk - 135:, 580:1340] = True      # sohbet satirlari
    m[:45, :200] = True                 # sol ust etki simgeleri
    m[225:350, gen - 235:] = True       # sagdaki etkinlik simgesi (kirmizi gul vb.)
    return m


def esya_etiketleri(kare):
    """Yere dusen esya/yang isim kutularini (ince koyu cerceve + beyaz yazi) bulur: [(x, y), ...]"""
    yuk, gen = kare.shape[:2]
    koyu = (kare.max(axis=2) < 40).astype(np.uint8)
    yatay = cv2.morphologyEx(koyu, cv2.MORPH_OPEN, np.ones((1, 22), np.uint8))
    maske = arayuz_maskesi(yuk, gen)
    maske[:70, gen // 2 - 260:gen // 2 + 260] = True      # hedef penceresi
    maske[175:265, gen // 2 - 335:gen // 2 + 335] = True  # duyuru bandi
    yatay[maske] = 0
    _, _, ist, _ = cv2.connectedComponentsWithStats(yatay, 8)
    beyaz = kare.min(axis=2) > 160
    sonuc = []
    for x, y, w, hh, _ in ist[1:]:
        if hh > 3 or not 22 <= w <= 200:
            continue
        for dy in list(range(15, 21)) + list(range(30, 42)):   # tek satir ya da sahip adli iki satir
            y2 = y + dy
            if y2 + 1 >= yuk:
                break
            if koyu[y2, x:x + w].mean() >= 0.55:
                ic = beyaz[y + 3:y2 - 1, x + 2:x + w - 2]
                sol = koyu[y + 2:y2 - 1, max(0, x - 2):x + 2].any(axis=1).mean()
                sag = koyu[y + 2:y2 - 1, x + w - 3:x + w + 2].any(axis=1).mean()
                ickoyu = koyu[y + 3:y2 - 1, x + 3:x + w - 3].mean()
                if ic.sum() >= 8 and ic.mean() < 0.4 and sol > 0.8 and sag > 0.8 and ickoyu < 0.6:
                    sonuc.append((int(x + w // 2), int((y + y2) // 2)))
                break
    return sonuc


def acik_pencereler(kare, kapat_sablon):
    """Acik oyun pencerelerinin (kizil baslik cubuklu) kapatma dugmeleri: [(x, y), ...]"""
    g = cv2.cvtColor(kare, cv2.COLOR_RGB2GRAY)
    r = cv2.matchTemplate(g, kapat_sablon, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(r >= 0.85)
    sonuc = []
    for x, y in zip(xs, ys):
        cx, cy = int(x) + kapat_sablon.shape[1] // 2, int(y) + kapat_sablon.shape[0] // 2
        if cx < 70 or (cy < 75 and abs(cx - kare.shape[1] // 2) < 320) or any(abs(cx - a) < 6 and abs(cy - b) < 6 for a, b in sonuc):
            continue
        sol = kare[max(0, cy - 4):cy + 5, cx - 60:cx - 25].reshape(-1, 3).mean(axis=0)
        if sol[0] > 85 and sol[0] > 1.6 * sol[1]:      # solunda kizil baslik cubugu var
            sonuc.append((cx, cy))
    return sonuc


def gorev_simgeleri(kare):
    """Sol kenardaki gorev parsomeni simgeleri (kirmizi kurdeleli), yukaridan asagi: [(x, y), ...]"""
    serit = kare[:kare.shape[0] - 170, :80].astype(int)
    m = ((serit[..., 0] > 170) & (serit[..., 1] < 55) & (serit[..., 2] < 55)).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((7, 7), np.uint8))
    n, _, ist, mer = cv2.connectedComponentsWithStats(m, 8)
    sonuc = []
    for i in range(1, n):
        x, y, w, hh, _ = ist[i]
        if 17 <= w <= 29 and 23 <= hh <= 35:
            sonuc.append((int(mer[i][0]), int(mer[i][1])))
    return sorted(sonuc, key=lambda p: p[1])


def orta_parlaklik(kare):
    yuk, gen = kare.shape[:2]
    return float(kare[int(yuk * 0.22):int(yuk * 0.62), gen // 2 - 260:gen // 2 + 260].mean())


def etki_sayisi(kare):
    """Sol ustteki etkin etki (guclendirme) simgelerinin sayisi (her renk)."""
    sayi = 0
    for i in range(12):
        x0 = 13 + 31 * i
        p = kare[12:41, x0:x0 + 28].astype(int)
        r, g, b = p[..., 0], p[..., 1], p[..., 2]
        camgobegi = (g > 180) & (b > 165) & (g > r + 45)          # cogu guclendirme simgesi
        kizil = (r > 60) & (r > g + 30) & (r > b + 30)            # hava kilici gibi koyu kirmizi zeminli simgeler
        if camgobegi.sum() >= 25 or (kizil.sum() >= 250 and (p.min(axis=2) > 170).sum() >= 8):
            sayi += 1
        else:
            break
    return sayi


_SU = {"acik": True, "log": 0.0}


def su_ilk_kontrol(kare):
    yuk, gen = kare.shape[:2]
    k = kare[int(yuk * 0.45):yuk - 160:8, 60:gen - 280:8].astype(int)
    return int(((k[..., 2] > k[..., 0] + 25) & (k[..., 2] > 90)).sum()) >= 40


def su_maskesi(kare):
    """Zemin bolgesinde (ekranin alt ~%55'i, arayuz haric) mavi-turkuaz doygun buyuk lekeler (nehir/gol).
    Donus (kucuk_maske, x_ofset, y_ofset, olcek). Kucuk/ince lekeler (kilic parlamasi vb.) acinimla elenir."""
    yuk, gen = kare.shape[:2]
    y0, x0 = int(yuk * 0.45), 60
    alt = cv2.resize(kare[y0:yuk - 160, x0:gen - 280], None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(alt, cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 0] >= 85) & (hsv[..., 0] <= 112) & (hsv[..., 1] >= 70) & (hsv[..., 2] >= 70)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, et, ist, _ = cv2.connectedComponentsWithStats(m, 8)
    out = np.zeros_like(m)
    for i in range(1, n):
        if ist[i][4] >= 190 and min(ist[i][2], ist[i][3]) >= 14 and ist[i][4] >= 0.3 * ist[i][2] * ist[i][3]:   # genis+dolgun leke: kilic parlamasi/ince seritler elenir
            out[et == i] = 1
    return out, x0, y0, 4


def su_var(su, x, y):
    m, x0, y0, o = su
    cx, cy = int((x - x0) / o), int((y - y0) / o)
    if not (0 <= cy < m.shape[0] and 0 <= cx < m.shape[1]):
        return False
    return bool(m[max(0, cy - 2):cy + 3, max(0, cx - 2):cx + 3].any())


def bos_yon(kare, aci, rx=230, ry=150, engeller=None):
    """Karakterden 'aci' (radyan, ekran) yonune en yakin, yolunda yaratik govdesi olmayan yonu bulur.
    Donus: (x, y) tiklanacak ekran noktasi."""
    yuk, gen = kare.shape[:2]
    kx, ky = gen // 2, int(yuk * 0.58)
    if engeller is None:
        engeller = [(x, y + 45) for x, y, *_ in kirmizi_etiketler(kare)]   # etiketin altindaki govde
    en_iyi, en_puan, en_sapma = None, None, 0
    su = su_maskesi(kare) if _SU["acik"] and su_ilk_kontrol(kare) else None
    su_sapma0 = False
    for sapma in (0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180):
        a = aci + math.radians(sapma)
        tx, ty = kx + rx * math.cos(a), ky + ry * math.sin(a)
        if not (60 < tx < gen - 280 and 90 < ty < yuk - 160):          # arayuz / ekran disi
            continue
        engel = 0
        for ex, ey in engeller:                                         # dogru parcasina uzaklik
            vx, vy = tx - kx, ty - ky
            t = max(0.0, min(1.0, ((ex - kx) * vx + (ey - ky) * vy) / (vx * vx + vy * vy or 1)))
            if math.hypot(ex - (kx + t * vx), ey - (ky + t * vy)) < 70:
                engel += 1
        if su is not None:                                              # suya giden yon: engel say
            say = 0
            for t_ in (0.5, 0.75, 1.0):
                px, py = kx + t_ * (tx - kx), ky + t_ * (ty - ky)
                if math.hypot(px - kx, py - ky) >= 150 and su_var(su, px, py):   # karakterin kendi parlamasi sayilmasin
                    say += 1
            if say >= 2:
                engel += 3
                if sapma == 0:
                    su_sapma0 = True
        puan = engel * 100 + abs(sapma)
        if en_puan is None or puan < en_puan:
            en_iyi, en_puan = (int(tx), int(ty)), puan
            en_sapma = sapma
    if su_sapma0 and en_iyi and en_sapma != 0 and time.time() - _SU["log"] > 10:
        _SU["log"] = time.time()
        print(f"{time.strftime('%H:%M:%S')}  engel: su yonu atlandi (secilen sapma {en_sapma} derece)")
    return en_iyi or (kx, ky + 150)


def gorev_ucgenleri(kare):
    """Gorev veren NPC'nin basindaki acik sari ucgen isaretleri: [(x, y), ...]"""
    p = kare.astype(int)
    m = ((p[..., 0] > 240) & (p[..., 1] > 230) & (p[..., 2] > 110) & (p[..., 2] < 210)).astype(np.uint8)
    m[arayuz_maskesi(*kare.shape[:2])] = 0
    n, _, ist, mer = cv2.connectedComponentsWithStats(m, 8)
    return [(int(mer[i][0]), int(mer[i][1]), int(ist[i][3])) for i in range(1, n)
            if 40 <= ist[i][4] <= 3500 and 12 <= ist[i][2] <= 90 and 10 <= ist[i][3] <= 90
            and ist[i][2] < ist[i][3] * 1.8 and ist[i][3] < ist[i][2] * 1.8]


def oyuncu_seviyesi(kare):
    """Karakterin basinin ustundeki yesil 'Lv N' yazisindan kendi seviyesini okur (isim rengi ne olursa olsun).
    Okunamazsa None."""
    yuk, gen = kare.shape[:2]
    x0, x1, y0, y1 = gen // 2 - 130, gen // 2 + 40, int(yuk * 0.40), int(yuk * 0.46)
    y = rakam.yesillik(kare[y0:y1, x0:x1])
    m = y > 45
    sutun = np.where(m.sum(axis=0) >= 1)[0]
    if len(sutun) < 6:
        return None
    # sutunlari kumelere ayir (8 pikselden buyuk bosluk yeni kume); beklenen yere en yakin kumeyi al
    kumeler, bas = [], sutun[0]
    for i in range(1, len(sutun)):
        if sutun[i] - sutun[i - 1] > 8:
            kumeler.append((bas, sutun[i - 1]))
            bas = sutun[i]
    kumeler.append((bas, sutun[-1]))
    kumeler = [k for k in kumeler if 14 <= k[1] - k[0] <= 48]
    if not kumeler:
        return None
    beklenen = gen // 2 - 48 - x0
    ka, kb = min(kumeler, key=lambda k: abs((k[0] + k[1]) / 2 - beklenen))
    satir = np.where(m[:, ka:kb + 1].any(axis=1))[0]
    return rakam.seviye_oku(kare, x0 + kb + 2, y0 + satir[0] - 1, y0 + satir[-1] + 2)


def yaratik_seviyesi(kare, etiket):
    x, y, w, hh = etiket
    return rakam.seviye_oku(kare, x - w // 2, y - hh - 1, y + 2)


def govde_noktasi(kare, alt):
    """Secili yaratigin tiklanacak govde noktasi (halkanin ustundeki isim etiketinden)."""
    halka = secim_halkasi(kare)
    if not halka:
        return None
    yakin = [t for t in kirmizi_etiketler(kare) if abs(t[0] - halka[0]) < 90 and 0 < halka[1] - t[1] < 170]
    if yakin:
        t = min(yakin, key=lambda t: abs(t[0] - halka[0]) + (halka[1] - t[1]))
        return int(t[0]), int(t[1]) + alt
    return halka[0], halka[1] - 30


def _bitisik_ayir(kare, maske, x, y, w, hh):
    """Buyuk kirmizi lekenin (ust uste isimler) icindeki her yesil 'Lv N'den sagindaki ismi ayirir."""
    yk, gn = maske.shape
    x0, y0, x1, y1 = max(0, x - 60), max(0, y - 2), min(gn, x + w + 4), min(yk, y + hh + 2)
    p = kare[y0:y1, x0:x1].astype(int)
    yesil = ((p[..., 1] > 140) & (p[..., 0] < 170) & (p[..., 2] < 100)).astype(np.uint8)
    n, _, ist, _ = cv2.connectedComponentsWithStats(cv2.dilate(yesil, np.ones((3, 5), np.uint8)), 8)
    sonuc = []
    for i in range(1, n):
        gx, gy, gw, gh, ga = ist[i]
        if not (6 <= gh <= 20 and 10 <= gw <= 60 and ga >= 8):
            continue
        ry0, ry1 = y0 + gy - 1, y0 + gy + gh + 1
        bas = x0 + gx + gw + 1
        sutun = maske[max(0, ry0):ry1, bas:min(gn, bas + 230)].any(axis=0)
        if not sutun[:12].any():
            continue
        son, bosluk = 0, 0
        for j, d in enumerate(sutun):                     # bitisik kirmizi sutunlar (en cok 10 px bosluk)
            if d:
                son, bosluk = j, 0
            else:
                bosluk += 1
                if bosluk > 10:
                    break
        ilk = int(np.argmax(sutun))
        ew = son - ilk + 1
        if ew < 22:
            continue
        ex0 = bas + ilk
        dolu = maske[max(0, ry0):ry1, ex0:ex0 + ew].sum()
        if dolu >= 25:
            sonuc.append((ex0 + ew // 2, ry1, ew + 12, ry1 - max(0, ry0)))   # +12: tek etiketteki genislemeyle uyumlu
    return sonuc


def kirmizi_etiketler(kare):
    """Yaratik isim yazilarini (kirmizi) bulur. Donus: [(x_orta, y_alt, gen, yuk), ...]"""
    r, g, b = cv2.split(kare)
    maske = (r > 120) & (cv2.subtract(r, g) > 85) & (cv2.subtract(r, b) > 75) & (g < 90)   # toprak zeminde de
    maske &= ~arayuz_maskesi(*kare.shape[:2])
    m8 = maske.astype(np.uint8) * 255
    m8 = cv2.dilate(m8, cv2.getStructuringElement(cv2.MORPH_RECT, (13, 3)))
    n, _, ist, _ = cv2.connectedComponentsWithStats(m8, 8)
    sonuc = []
    for i in range(1, n):
        x, y, w, hh, alan = ist[i]
        if (w > 260 or hh > 22) and w < 900 and hh < 160:   # ust uste binmis isimler: yesil "Lv" baslarindan ayir
            sonuc.extend(_bitisik_ayir(kare, maske, x, y, w, hh))
            continue
        if 22 <= w <= 260 and 8 <= hh <= 22:
            dolu = maske[y:y + hh, x:x + w].sum()
            if dolu >= 25 and dolu / (w * hh) < 0.6:   # yazi: seyrek dolu; duz kirmizi leke degil
                # gercek yaratik isminin solunda yesil "Lv N" yazisi olur; arayuz simgelerinde olmaz
                sol = kare[y:y + hh, max(0, x - 55):x].astype(int)
                yesil = ((sol[..., 1] > 140) & (sol[..., 0] < 170) & (sol[..., 2] < 100)).sum()
                if yesil >= 8:
                    sonuc.append((x + w // 2, y + hh, w, hh))
    return sonuc


def beyaz_etiketler(kare):
    """Beyaz isim yazilari (solunda yesil 'Lv N' olanlar = metin taslari). Donus: [(x_orta, y_alt, gen, yuk), ...]"""
    p = kare.astype(int)
    mx, mn = p.max(axis=2), p.min(axis=2)
    maske = (mn > 175) & (mx - mn < 45)
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


def metin_taslari(kare, sablon):
    """Metin tasi isim sablonunu arar. Donus: [(x_orta, y_alt, gen, yuk), ...]"""
    if sablon is None:
        return []
    gri = cv2.cvtColor(kare, cv2.COLOR_RGB2GRAY)
    s = cv2.matchTemplate(gri, sablon, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(s >= 0.82)
    th, tw = sablon.shape
    sonuc = []
    for x, y in sorted(zip(xs, ys), key=lambda p: -s[p[1], p[0]]):
        if all(abs(x - a) > tw or abs(y - bb) > th for a, bb, _, _ in sonuc):
            sonuc.append((x, y, tw, th))
    return [(x + tw // 2, y + th, tw, th) for x, y, tw, th in sonuc]


def _sivi_rengi(parca):
    """Parcadaki doygun (renkli) piksellerin ortalama rengi; yoksa None."""
    p = parca.astype(int).reshape(-1, 3)
    q = p[(p.max(axis=1) - p.min(axis=1)) > 70]
    return q.mean(axis=0) if len(q) >= 12 else None


def esya_bul(kare, sablon_rgb, esik=0.62, renk_farki=45):
    """Envanter esyasini bicim + RENK ile arar (gri eslesme mor iksiri mavi/kirmizi iksirle karistiriyordu;
    parlayan zemin de puani dusuruyor). Merkezini (x, y) dondurur, yoksa None."""
    gri = cv2.cvtColor(kare, cv2.COLOR_RGB2GRAY)
    s = cv2.matchTemplate(gri, cv2.cvtColor(sablon_rgb, cv2.COLOR_RGB2GRAY), cv2.TM_CCOEFF_NORMED)
    sh, sw = sablon_rgb.shape[:2]
    hedef = _sivi_rengi(sablon_rgb)
    for _ in range(12):
        _, en, _, yer = cv2.minMaxLoc(s)
        if en < esik:
            return None
        renk = _sivi_rengi(kare[yer[1]:yer[1] + sh, yer[0]:yer[0] + sw])
        if hedef is None or (renk is not None and np.abs(renk - hedef).max() < renk_farki):
            return yer[0] + sw // 2, yer[1] + sh // 2
        cv2.rectangle(s, (yer[0] - 10, yer[1] - 10), (yer[0] + 10, yer[1] + 10), -1.0, -1)
    return None


def simge_bul(kare, sablon, esik=0.85):
    """Bir simge sablonunu karede arar; merkezini (x, y) dondurur, yoksa None."""
    gri = cv2.cvtColor(kare, cv2.COLOR_RGB2GRAY)
    s = cv2.matchTemplate(gri, sablon, cv2.TM_CCOEFF_NORMED)
    _, en, _, yer = cv2.minMaxLoc(s)
    if en < esik:
        return None
    return yer[0] + sablon.shape[1] // 2, yer[1] + sablon.shape[0] // 2


def can_orani(kare):
    """Sol alttaki kirmizi can cubugunun doluluk orani (0-1)."""
    yuk = kare.shape[0]
    serit = kare[yuk - 40:yuk - 30, 74:189].astype(int)
    kirmizi = (serit[..., 0] > 150) & (serit[..., 1] < 100) & (serit[..., 2] < 110)
    sutun = kirmizi.any(axis=0)
    return float(sutun.mean())


def mana_orani(kare):
    """Sol alttaki mavi mana cubugunun doluluk orani (0-1)."""
    yuk = kare.shape[0]
    serit = kare[yuk - 26:yuk - 16, 74:189].astype(int)
    mavi = (serit[..., 2] > 150) & (serit[..., 0] < 110)
    return float(mavi.any(axis=0).mean())


def hedef_cani(kare):
    """Ust ortadaki hedef penceresinin can cubugu (0-1). Hedef secili degilse 0."""
    gen = kare.shape[1]
    serit = kare[38:40, gen // 2 + 42:gen // 2 + 179].astype(int)
    kirmizi = (serit[..., 0] > 110) & (serit[..., 1] < 50) & (serit[..., 2] < 50)
    return float(kirmizi.all(axis=0).mean())


def secim_halkasi(kare):
    """Secili yaratigin ayagindaki parlak kirmizi halkanin merkezi; yoksa None."""
    r, g, b = kare[..., 0].astype(int), kare[..., 1].astype(int), kare[..., 2].astype(int)
    maske = (r > 235) & (g < 95) & (b < 60)
    maske &= ~arayuz_maskesi(*kare.shape[:2])
    m8 = cv2.dilate(maske.astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 15)))
    n, _, ist, merkez = cv2.connectedComponentsWithStats(m8, 8)
    en_iyi, alan_max = None, 0
    for i in range(1, n):
        x, y, w, hh, alan = ist[i]
        if w >= 50 and maske[y:y + hh, x:x + w].sum() >= 80 and alan > alan_max:
            en_iyi, alan_max = (int(merkez[i][0]), int(merkez[i][1])), alan
    return en_iyi


def seviye_hanesi(kare, etiket):
    """Etiketin solundaki yesil 'Lv N' yazisinin genisliginden seviyenin kac haneli oldugunu kestirir."""
    x, y, w, hh = etiket
    sol = x - w // 2
    p = kare[max(0, y - hh - 1):y + 2, max(0, sol - 55):sol].astype(int)
    m = (p[..., 1] > 110) & (p[..., 1] > p[..., 0] + 25) & (p[..., 2] < 110)
    sutun = np.where(m.sum(axis=0) >= 2)[0]
    if len(sutun) < 4:
        return 0
    return 2 if sutun[-1] - sutun[0] >= 27 else 1


def en_yakin(hedefler, merkez):
    return min(hedefler, key=lambda t: math.hypot(t[0] - merkez[0], t[1] - merkez[1]))


def ciz(kare, yaratik, tas, can, yol):
    bgr = cv2.cvtColor(kare, cv2.COLOR_RGB2BGR)
    for x, y, w, hh in yaratik:
        cv2.rectangle(bgr, (x - w // 2, y - hh), (x + w // 2, y), (0, 255, 255), 1)
        cv2.circle(bgr, (x, y + 45), 5, (0, 255, 255), -1)
    for x, y, w, hh in tas:
        cv2.rectangle(bgr, (x - w // 2, y - hh), (x + w // 2, y), (255, 0, 255), 2)
    cv2.putText(bgr, f"can %{can * 100:.0f}  yaratik {len(yaratik)}  tas {len(tas)}", (220, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.imwrite(yol, bgr)


def bilgi_yukle():
    """harita_bilgisi.json: internetten derlenen seviye -> harita -> canavar tablosu (oyunda gorulen esastir)."""
    try:
        with open(os.path.join(KLASOR, "harita_bilgisi.json"), encoding="utf-8") as f:
            b = json.load(f)
    except Exception:
        return {"haritalar": [], "seviye_onerisi": [], "canavar_lv": {}}
    b["canavar_lv"] = {}
    for hrt in b.get("haritalar", []):
        for ad, lv in hrt.get("canavarlar", []) + hrt.get("metinler", []):
            b["canavar_lv"][" ".join(oku.sade(ad).split())] = lv
    return b


def esya_tablosu_bul(ad):
    """esya_avi.json'da adi tutan esya (dict) ya da None."""
    try:
        with open(os.path.join(KLASOR, "esya_avi.json"), encoding="utf-8") as f:
            liste = json.load(f).get("esyalar", [])
    except Exception:
        return None
    hedef = " ".join(oku.sade(ad).split())
    return next((e for e in liste if " ".join(oku.sade(e["ad"]).split()) == hedef), None)


def plan_hesapla(bilgi, sev, harita_adi="monastry"):
    """Seviyeme gore: bulundugum haritada mi kalmali, hangi canavarlar hedef. Donus: dict."""
    if not sev:
        return {"yazi": "seviye bilinmiyor"}
    oneri = next((o for o in bilgi.get("seviye_onerisi", []) if o["seviye"][0] <= sev < o["seviye"][1]), None)
    simdiki = bilgi.get("harita_eslesme", {}).get(harita_adi, "")
    hrt = next((x for x in bilgi.get("haritalar", []) if x["ad"] == simdiki), None)
    hedef = []
    if hrt:
        hedef = [ad for ad, lv in hrt.get("canavarlar", []) if sev - 2 <= lv <= sev + 3]
    gecis = bool(oneri and simdiki and oneri["harita"] != simdiki)
    yazi = (f"Lv {sev}: " + (f"{oneri['harita']} onerilir" if oneri else "oneri yok")
            + (f" (su an {simdiki}) - HARITA DEGISTIRME ZAMANI" if gecis else "")
            + (f"; hedef canavarlar: {', '.join(hedef)}" if hedef else ""))
    return {"yazi": yazi, "hedef": hedef, "gecis": gecis, "oneri": oneri["harita"] if oneri else ""}


# ---------------------------------------------------------------- dongu
def calistir(ayar, sablon):
    _SU["acik"] = bool(ayar.get("su_kacin", True))
    import keyboard
    import pydirectinput
    pydirectinput.PAUSE = 0.03
    pydirectinput.FAILSAFE = False

    h = pencere_bul(ayar["pencere_basligi"])
    if not h:
        sys.exit("Oyun penceresi bulunamadi.")
    durum = {"calis": True, "duraklat": False}
    su_an = ["baslangic"]          # su an ne yapiliyor (duraklama bekcisi loga yazar)

    # GUVENLIK: oyun penceresi onde degilse hicbir tus/fare girdisi gonderilmez
    # (yoksa '1' gibi tuslar o an acik olan baska pencereye yazilir).
    def _korumali(asil, bekle=False, tiklama=False):
        def sarmal(*a, **k):
            while bekle and win32gui.GetForegroundWindow() != h and durum["calis"]:
                time.sleep(0.3)
            if win32gui.GetForegroundWindow() != h:
                return None
            if tiklama:                      # MARKET KORUMASI: sol alttaki Indirim/Markete Git kutusuna tiklama yok
                try:
                    mx_, my_ = win32api.GetCursorPos()
                    ox_, oy_, gen_, yuk_ = istemci_kutusu(h)
                    if mx_ - ox_ < 280 and my_ - oy_ > yuk_ - 270:
                        print(f"{time.strftime('%H:%M:%S')}  KORUMA: sol alt (Markete Git) bolgesine tiklama engellendi")
                        return None
                    if mx_ - ox_ > gen_ - 70 and my_ - oy_ > yuk_ - 50:
                        print(f"{time.strftime('%H:%M:%S')}  KORUMA: sistem menusu dugmesine tiklama engellendi")
                        return None
                except Exception:
                    pass
            sonuc_ = asil(*a, **k)
            if asil is _asil_press and a and a[0] == "esc":
                esc_kontrol()
            return sonuc_
        return sarmal

    import win32api
    _asil_press = pydirectinput.press

    def esc_kontrol():
        """Esc sistem menusunu actiysa (giris ekranina don / karakter degistir) hemen kapat."""
        try:
            time.sleep(0.2)
            k_ = kare_al(h)
            yk_, gn_ = k_.shape[:2]
            y_ = oku.sade(" ".join(t["yazi"] for t in oku.oku(k_, kutu=(gn_ // 2 - 300, yk_ * 0.2, gn_ // 2 + 300, yk_ * 0.8), olcek=2)))
            if sum(1 for w in ("giris ekran", "karakter degis", "oyundan cik", "sistem", "secenek", "kanal degis") if w in y_) >= 2:
                print(f"{time.strftime('%H:%M:%S')}  KORUMA: sistem menusu acildi - kapatiliyor")
                _asil_press("esc")
                time.sleep(0.2)
        except Exception:
            pass

    for _ad in ("press", "keyDown", "click", "moveTo", "mouseDown"):
        setattr(pydirectinput, _ad, _korumali(getattr(pydirectinput, _ad), tiklama=_ad in ("click", "mouseDown")))
    pydirectinput.keyUp = pydirectinput.keyUp          # tus birakma her zaman gitsin (takili kalmasin)
    pydirectinput.mouseUp = pydirectinput.mouseUp
    keyboard.add_hotkey("f12", lambda: durum.update(calis=False))
    keyboard.add_hotkey("f10", lambda: durum.update(duraklat=not durum["duraklat"]))
    print("Bot hazir. Oyun penceresine gec. F10 duraklat/devam, F12 kapat.")

    bos_tur = olu_kare = kesilen = 0
    son_beceri = 0.0
    try:
        with open(os.path.join(KLASOR, "durum.json"), encoding="utf-8") as f_:
            benim_sev = json.load(f_).get("son_seviye")      # son okunan seviye; okununca guncellenir
    except Exception:
        benim_sev = None
    spotta = False
    ox_son = [0, 0]
    son_statu = 0.0
    son_izleme = 0.0
    son_pencere = 0.0
    son_gorev = time.time() - 9999
    gorev_sira = 0
    gorev_deneme = {}
    aranan_durum = []             # gorev yazisindan okunan, one alinacak yaratik adlari
    av_aranan = []                # av gorevinin o an istedigi yaratik (gorev listesinden okunur)
    son_saldiri_b = {}
    yol_k = os.path.join(KLASOR, "sablon", "kapat.png")
    kapat_s = cv2.imread(yol_k, cv2.IMREAD_GRAYSCALE) if os.path.exists(yol_k) else None
    yol_s, yol_a = os.path.join(KLASOR, "sablon", "statu_simge.png"), os.path.join(KLASOR, "sablon", "arti.png")
    statu_simge = cv2.imread(yol_s, cv2.IMREAD_GRAYSCALE) if os.path.exists(yol_s) and os.path.exists(yol_a) else None
    arti = cv2.imread(yol_a, cv2.IMREAD_GRAYSCALE) if statu_simge is not None else None
    envanter = []
    try:
        with open(os.path.join(KLASOR, "durum.json"), encoding="utf-8") as f_:
            _d0 = json.load(f_)
    except Exception:
        _d0 = {}
    for e in ayar["envanter_kullan"]:
        yol_e = os.path.join(KLASOR, "sablon", e["sablon"])
        if os.path.exists(yol_e):
            ad_ = e["sablon"][:-4]
            sure_ = _d0.get("iksir_sure", {}).get(ad_, e["aralik_sn"])     # ogrenilmis etki suresi
            icildi_ = _d0.get("iksir_icildi", {}).get(ad_, 0)
            if e.get("sabit"):
                sure_ = e["aralik_sn"]                                       # sabit aralik (ejderha tanrisi)
            envanter.append({"ad": ad_, "sablon": cv2.cvtColor(cv2.imread(yol_e), cv2.COLOR_BGR2RGB),
                             "sure": sure_, "icildi": icildi_, "ayni": False, "sandik": "sandik" in ad_,
                             "sabit": bool(e.get("sabit")) or bool(e.get("olunce")),
                             "olunce": bool(e.get("olunce")),
                             "sonraki": float("inf") if e.get("olunce") else max(time.time() + 5, icildi_ + sure_)})
    saldiri_basili = False

    def birak():
        nonlocal saldiri_basili
        if saldiri_basili:
            pydirectinput.keyUp(ayar["saldiri_tusu"])
            saldiri_basili = False

    def topla():
        su_an[0] = "topla"
        """Toplama tusuna basar; yerde esya etiketi goruyorsa ustune tiklayip alir."""
        for _ in range(3):
            pydirectinput.press(ayar["toplama_tusu"])
            time.sleep(0.1)
        if not ayar["esyaya_tikla"]:
            return
        bas_t = time.time()
        for _ in range(ayar["en_cok_esya"]):
            if time.time() - bas_t > ayar["toplama_en_uzun_sn"]:
                return
            k = kare_al(h)
            ox_, oy_, gen_, yuk_ = istemci_kutusu(h)
            kx, ky = gen_ // 2, int(yuk_ * 0.58)
            yakin = [e for e in esya_etiketleri(k) if math.hypot(e[0] - kx, e[1] - ky) < ayar["esya_yaricapi_piksel"]]
            if not yakin or win32gui.GetForegroundWindow() != h:
                return
            ex, ey = min(yakin, key=lambda e: math.hypot(e[0] - kx, e[1] - ky))
            pydirectinput.moveTo(ox_ + ex, oy_ + ey)
            time.sleep(0.05)
            pydirectinput.click()
            time.sleep(0.25 + math.hypot(ex - kx, ey - ky) / 700)
            pydirectinput.press(ayar["toplama_tusu"])
            time.sleep(0.08)

    def sec(hx, hy):
        su_an[0] = "sec"
        """Yaratiga tiklar; hedef penceresi acildiysa True."""
        for alt in (ayar["etiket_alti_piksel"], 25, 70):
            pydirectinput.moveTo(ox_son[0] + int(hx), ox_son[1] + int(hy) + alt)
            time.sleep(0.06)
            pydirectinput.click()
            for _ in range(6):
                time.sleep(0.06)
                if hedef_cani(kare_al(h)) > 0.03:
                    return True
        return False

    def mini_harita(k):
        gen_ = k.shape[1]
        m = k[30:140, gen_ - 140:gen_ - 30].astype(int)
        kir = (m[..., 0] > 140) & (m[..., 1] < 90)            # yaratik noktalari (hareket eder) sayilmasin
        g = m.mean(axis=2).astype(np.float32)
        g[kir] = 0
        return cv2.GaussianBlur(g, (5, 5), 0), kir

    def hizli_baslat(aci=None, devam=None):
        """Savas disi yuruyus icin hizli takilma izleyicisi (aci: ekranda gidilen yon, devam: yeniden tiklanacak nokta)."""
        return {"t0": time.time(), "gec": [], "son": 0.0, "aci": aci, "devam": devam}

    def hizli_adim(st, kf):
        """Karakter yurumesi beklenirken mini harita 0.8 sn kipirdamadiysa bos yone (60-120 derece sapan) 1 adim
        tiklar, hedefe devam eder. True: yan adim atildi. Savasta cagrilmaz."""
        if not ayar.get("hizli_engel", True):
            return False
        simdi = time.time()
        mh, kir = mini_harita(kf)
        st["gec"].append((simdi, mh, kir))
        st["gec"] = [g for g in st["gec"] if simdi - g[0] < 2.0]
        if simdi - st["t0"] < 0.5 or simdi - st["son"] < 2.5:
            return False
        eski = [g for g in st["gec"] if simdi - g[0] >= 0.8]
        if not eski:
            return False
        _, mh0, kir0 = eski[-1]
        ort = ~(kir | kir0)
        fark = float(np.abs(mh - mh0)[ort].mean()) if ort.any() else 99.0
        if fark >= 0.6:
            return False
        st["son"], st["gec"] = simdi, []
        a = st["aci"] if st["aci"] is not None else random.uniform(0, 2 * math.pi)
        a += random.choice((-1, 1)) * math.radians(random.uniform(60, 120))
        print(f"{time.strftime('%H:%M:%S')}  engel: hizli yon degisimi (0.8 sn kipirdamadi, fark {fark:.2f})")
        tikla(*bos_yon(kf, a, 200, 130))
        if st["devam"] is not None:
            time.sleep(0.8)
            tikla(*st["devam"])
        return True

    def vurus_bekle(sure_sn, yana_kac=True):
        su_an[0] = "vurus_bekle"
        """Secili hedefe ilk vurus isabet edene (cani dusene) ya da hedef olene kadar bekler.
        Mini harita 1 sn boyunca kaymiyorsa karakter takilmistir (agac, ev, slot): once yana kacip
        hedefe yeniden tiklar, yine takilirsa False doner."""
        ilk, bit = None, time.time() + sure_sn
        gecmis, durgun_bas, kacis = [], None, 0
        while time.time() < bit and durum["calis"] and not durum["duraklat"]:
            k = kare_al(h)
            if olum_denetle(k):
                return False
            hc = hedef_cani(k)
            if hc <= 0.03:
                return True
            if ilk is None:
                ilk = hc
            elif hc < ilk - 0.01:
                return True
            simdi = time.time()
            mh, kir = mini_harita(k)
            gecmis.append((simdi, mh, kir))
            eski = [g for g in gecmis if simdi - g[0] >= 1.0]
            if eski:
                _, mh0, kir0 = eski[-1]
                ort = ~(kir | kir0)
                fark = float(np.abs(mh - mh0)[ort].mean()) if ort.any() else 99.0
                if fark < ayar["takilma_esik"]:
                    durgun_bas = durgun_bas or simdi
                    if simdi - durgun_bas > ayar["takilma_sn"]:
                        if yana_kac and kacis < 1:
                            kacis += 1
                            yuk_, gen_ = k.shape[:2]
                            kx, ky = gen_ // 2, int(yuk_ * 0.58)
                            nokta = govde_noktasi(k, ayar["etiket_alti_piksel"])
                            hx, hy = nokta if nokta else (kx, ky - 200)
                            dx, dy = hx - kx, hy - ky
                            boy = math.hypot(dx, dy) or 1.0
                            hedef_aci = math.atan2(dy, dx)
                            engel_ = [(x, y + 45) for x, y, *_ in kirmizi_etiketler(k)
                                      if math.hypot(x - hx, y + 45 - hy) > 40]          # hedefin kendisi engel degil
                            tikla(*bos_yon(k, hedef_aci + math.pi / 2, 170, 110, engel_))   # bos yana kac
                            time.sleep(1.1)
                            if nokta:
                                tikla(*nokta)                   # hedefe yeniden yuru
                            gecmis, durgun_bas = [], None
                            bit = max(bit, time.time() + 4)
                            continue
                        son_neden[0] = "takildi"
                        return False
                else:
                    durgun_bas = None
            gecmis = [g for g in gecmis if simdi - g[0] < 2.5]
            if can_orani(k) < ayar["can_esigi"]:
                pydirectinput.press(ayar["can_potu_tusu"])
            time.sleep(0.12)
        son_neden[0] = "sure doldu"
        return False

    def etrafa_bak(sure):
        su_an[0] = "etrafa_bak"
        """Kamerayi SUREKLI dondururken her karede bakar; slot (ya da metin tasi) gorunce hemen durur."""
        pydirectinput.keyDown(ayar["kamera_tusu"])
        bas_ = time.time()
        try:
            while time.time() - bas_ < sure and durum["calis"] and not durum["duraklat"]:
                k_ = kare_al(h)
                tum_ = kirmizi_etiketler(k_)
                if ayar["sadece_hedefler"]:
                    if sadece_suz(k_, tum_):
                        return True
                    tum_ = []
                for t in tum_:
                    if sum(1 for u in tum_ if math.hypot(t[0] - u[0], t[1] - u[1]) < ayar["slot_yaricapi_piksel"]) \
                            >= ayar["slot_en_az"]:
                        return True
                if ayar["metin_kes"] and beyaz_etiketler(k_):
                    return True
                time.sleep(0.02)
            return False
        finally:
            pydirectinput.keyUp(ayar["kamera_tusu"])

    _menzil_yol = os.path.join(KLASOR, "menzil.json")
    try:
        with open(_menzil_yol, encoding="utf-8") as _f:
            menzil_ornek = list(json.load(_f))[-300:]
    except Exception:
        menzil_ornek = []
    menzil_d = {"son": 0.0, "yaz": 0.0}

    def menzil():
        """Ogrenilen vurma mesafesi (piksel): vurus tutarken secim halkasinin karaktere uzakligi, %85'lik dilim."""
        if len(menzil_ornek) < 15:
            return 170.0
        s_ = sorted(menzil_ornek)
        return float(min(200, max(90, s_[int(len(s_) * 0.70)])))   # %70 dilim: uzaktan vuran beceri (kilic cevirme) ornekleri sismesin

    def menzil_kaydet(k_, gen_, yuk_):
        """Can dusurdugumuz anda hedefin uzakligini kaydet (saniyede en cok 1)."""
        if time.time() - menzil_d["son"] < 1.0:
            return
        menzil_d["son"] = time.time()
        halka_ = secim_halkasi(k_)
        if not halka_:
            return
        menzil_ornek.append(round(math.hypot(halka_[0] - gen_ // 2, halka_[1] - int(yuk_ * 0.60)), 1))
        del menzil_ornek[:-300]
        if len(menzil_ornek) % 25 == 0:
            print(f"{time.strftime('%H:%M:%S')}  menzil: ogrenilen vurma mesafesi {menzil():.0f} px ({len(menzil_ornek)} ornek)")
        if time.time() - menzil_d["yaz"] > 60:
            menzil_d["yaz"] = time.time()
            try:
                with open(_menzil_yol, "w", encoding="utf-8") as _f:
                    json.dump(menzil_ornek, _f)
            except Exception:
                pass

    def vurus_sabri(k_, gen_, yuk_, son_degisim_):
        """Hedefin cani dusmezse kac sn beklensin: hedef menzil disindaysa (secim halkasi karakterden uzak)
        bosuna sallamasin - hemen yaklassin; yakinsa guclu yaratik olabilir - biraz daha sabret."""
        if not ayar.get("ince_vurus", True):
            return 2.5
        if time.time() - son_degisim_ < 0.9:
            return 2.5
        halka_ = secim_halkasi(k_)
        if halka_ and math.hypot(halka_[0] - gen_ // 2, halka_[1] - int(yuk_ * 0.60)) > menzil() * 1.15:
            return 0.7                                  # ogrenilen vurma mesafesinin disinda: bosa vuruyor, hemen yuru
        return 2.0 if halka_ else 2.5                   # menzilde ama can dusmuyor (yanlis yone bakiyor olabilir): 2 sn sonra tikla

    def kacin(hx, hy, neden=""):
        su_an[0] = "kacin"
        """Ulasilamayan hedeften uzaklas: hedefin ters yonune yuru, kamerayi cevir."""
        nonlocal ulasilamayan
        ulasilamayan += 1
        k = kare_al(h)
        yuk_, gen_ = k.shape[:2]
        kx, ky = gen_ // 2, int(yuk_ * 0.58)
        dx, dy = kx - hx, ky - hy
        boy = math.hypot(dx, dy) or 1.0
        atla.append((time.time(), hx, hy))
        del atla[:-12]
        diger_ = [t for t in kirmizi_etiketler(k) if math.hypot(t[0] - hx, t[1] - hy) > 60
                  and math.hypot(t[0] - kx, t[1] - ky) < 450]
        son_atla_ = [z for z, _, _ in atla if time.time() - z < 25]
        if len(son_atla_) >= 3:                               # ust uste ulasilamiyor (cit, pazar, ev): buradan ayril
            print(f"{time.strftime('%H:%M:%S')}  hedefe ulasilamadi [{neden}] - 25 sn'de {len(son_atla_)}. kez, engel var: baska yere")
            atla.clear()
            try:
                engel_kaydet(neden or "ulasilamama")
            except Exception as e_eh:
                print("engel hafiza:", e_eh)
            tikla(*bos_yon(k, math.atan2(ky - hy, kx - hx), 430, 280))
            time.sleep(1.5)
            engel_kac[0] = True                               # ana dongu: haritadan baska bolgeye yuru
            return
        if diger_:                                            # yakinda kesilecek baska yaratik var: yerinde kal
            print(f"{time.strftime('%H:%M:%S')}  hedefe ulasilamadi [{neden}] - atlandi, yanimdaki {len(diger_)} yaratiktan devam")
            return
        aci = math.atan2(dy, dx) + random.uniform(-0.6, 0.6)
        print(f"{time.strftime('%H:%M:%S')}  hedefe ulasilamadi [{neden}] - bos yone gidiliyor")
        tx, ty = bos_yon(k, aci, 430, 280)
        tikla(tx, ty)
        time.sleep(2.2)
        pydirectinput.keyDown(ayar["kamera_tusu"])
        time.sleep(ayar["kamera_donus_sn"] * (1 + ulasilamayan % 3))
        pydirectinput.keyUp(ayar["kamera_tusu"])

    def yakindakiler(k, ust_sev, r_min, r_max, alt_sev=None):
        """Karaktere r_min-r_max piksel uzakliktaki, seviyesi uygun yaratik etiketleri (yakindan uzaga)."""
        yuk_, gen_ = k.shape[:2]
        kx, ky = gen_ // 2, int(yuk_ * 0.58)
        liste = []
        for t in kirmizi_etiketler(k):
            uzak = math.hypot(t[0] - kx, t[1] - ky)
            if not r_min <= uzak < r_max:
                continue
            if yolo_oyuncu_etiketi_mi(t[0], t[1]):
                if time.time() - _yolo.get("log_t", 0) > 30:
                    _yolo["log_t"] = time.time()
                    print(f"{time.strftime('%H:%M:%S')}  sekil: oyuncu sanilan etiket atlandi")
                continue
            sev = yaratik_seviyesi(k, t)
            if sev is None:
                if not 0 < seviye_hanesi(k, t) <= len(str(ust_sev)):
                    continue
            elif sev > ust_sev or (alt_sev is not None and sev < alt_sev):
                continue
            liste.append((dunya_uzak(t[0], t[1] + 45, kx, ky, ayar["derinlik_ufuk"], ayar["derinlik_carpan"])
                          if ayar["derinlik_sirala"] else uzak, t))
        return [t for _, t in sorted(liste, key=lambda s: s[0])]

    def statu_gelistir(k):
        su_an[0] = "statu_gelistir"
        """'Statu Gelistir' simgesi varsa karakter penceresini acip secili ozelligin artisina tiklar."""
        yuk_k = k.shape[0]
        yer = simge_bul(k[yuk_k - 200:, :500], statu_simge, 0.9)
        if yer is None:
            return False
        yer = (yer[0], yer[1] + yuk_k - 200)

        def artilar(kk):
            g = cv2.cvtColor(kk, cv2.COLOR_RGB2GRAY)
            r = cv2.matchTemplate(g, arti, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(r >= 0.8)
            sat = []
            for x, y in sorted(zip(xs, ys), key=lambda p: p[1]):
                if not sat or y - sat[-1][1] > 8:
                    sat.append((int(x) + arti.shape[1] // 2, int(y) + arti.shape[0] // 2))
            return sat

        acan = None
        sat = artilar(k)
        if len(sat) != 4:
            pydirectinput.moveTo(ox_son[0] + yer[0], ox_son[1] + yer[1])
            time.sleep(0.1)
            pydirectinput.click()
            acan = "simge"
            time.sleep(0.8)
            sat = artilar(kare_al(h))
            if len(sat) != 4:
                pydirectinput.press(ayar["karakter_tusu"])
                acan = "tus"
                time.sleep(0.8)
                sat = artilar(kare_al(h))
        if len(sat) != 4:                                       # pencere baska sekmede acilmis olabilir
            pencere = sorted(acik_pencereler(kare_al(h), kapat_s))
            if pencere:
                tikla(pencere[0][0] - 252, pencere[0][1] + 412)       # Durum sekmesi
                time.sleep(0.8)
                sat = artilar(kare_al(h))
        if len(sat) != 4:
            print(f"{time.strftime('%H:%M:%S')}  statu: arti dugmeleri bulunamadi ({len(sat)})")
            Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", "statu_hata.png"))
        sira = {"vit": 0, "int": 1, "str": 2, "dex": 3}[ayar["statu"]]
        n = 0
        while len(sat) == 4 and n < 30:
            pydirectinput.moveTo(ox_son[0] + sat[sira][0], ox_son[1] + sat[sira][1])
            time.sleep(0.06)
            pydirectinput.click()
            n += 1
            time.sleep(0.25)
            sat = artilar(kare_al(h))
        if n:
            print(f"{time.strftime('%H:%M:%S')}  statu: {ayar['statu'].upper()} +{n}")
        if acan:
            pydirectinput.press(ayar["karakter_tusu"])
            time.sleep(0.4)
        pydirectinput.moveTo(ox_son[0] + k.shape[1] // 2, ox_son[1] + int(k.shape[0] * 0.75))
        return True

    def tikla(x, y, sag=False):
        pydirectinput.moveTo(ox_son[0] + int(x), ox_son[1] + int(y))
        time.sleep(0.05)
        pydirectinput.click(button="right" if sag else "left")

    def yavas_tikla(x, y):
        """Arayuz dugmeleri icin: once uzerine gel, bekle, basili tutup birak (hizli tiklamayi dukkan almiyor)."""
        pydirectinput.moveTo(ox_son[0] + int(x), ox_son[1] + int(y))
        time.sleep(0.3)
        pydirectinput.mouseDown()
        time.sleep(0.1)
        pydirectinput.mouseUp()

    def pencereleri_kapat():
        for px, py in acik_pencereler(kare_al(h), kapat_s):
            tikla(px, py)
            time.sleep(0.3)

    def durum_oku():
        yol_d = os.path.join(KLASOR, "durum.json")
        if os.path.exists(yol_d):
            with open(yol_d, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def durum_yaz(**kw):
        d = durum_oku()
        d.update(kw)
        with open(os.path.join(KLASOR, "durum.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)

    def harita_ac():
        su_an[0] = "harita_ac"
        """Genel gorunum haritasini acar; kapat dugmesinin konumunu dondurur (yoksa None)."""
        pencereleri_kapat()
        k = kare_al(h)
        tikla(k.shape[1] - 139, 30)                             # mini haritadaki M dugmesi
        pencere = []
        for _ in range(10):
            time.sleep(0.12)
            pencere = acik_pencereler(kare_al(h), kapat_s)
            if pencere:
                break
        if not pencere:
            pydirectinput.press("m")
            time.sleep(1.2)
            pencere = acik_pencereler(kare_al(h), kapat_s)
        return pencere[0] if pencere else None

    def harita_npc_bul(anahtar):
        su_an[0] = "harita_npc_bul"
        """Haritayi acar, yesil noktalarin ustune gelip adi 'anahtar' iceren NPC'yi arar.
        Bulunan konum durum.json'a (harita kapat dugmesine gore) kaydedilir, sonraki seferde dogrudan kullanilir.
        Donus: (kapat_dugmesi, (x, y, ad)) ya da (kapat_dugmesi_ya_da_None, None)."""
        kapat_d = harita_ac()
        if kapat_d is None:
            print("harita: pencere acilamadi")
            return None, None
        cx, cy = kapat_d
        kayitli = durum_oku().get("npc_konum", {}).get(anahtar)
        if kayitli:
            return kapat_d, (cx + kayitli[0], cy + kayitli[1], anahtar)
        k = kare_al(h)
        x0, y0, x1, y1 = cx - 242, cy + 17, cx + 12, cy + 334  # harita resmi
        p = k[y0:y1, x0:x1].astype(int)
        m = ((p[..., 1] > 180) & (p[..., 0] < 140) & (p[..., 2] < 140)).astype(np.uint8) * 255
        n, _, ist, _ = cv2.connectedComponentsWithStats(m, 8)
        noktalar = []
        for i in range(1, n):
            x, y, w, hh, alan = ist[i]
            if alan < 10:
                continue
            if w > 7 or hh > 7:
                noktalar += [(int(x + 2), int(y + 2)), (int(x + w - 3), int(y + hh - 3))]
            else:
                noktalar.append((int(x + w // 2), int(y + hh // 2)))
        for nx, ny in noktalar[:40]:
            ax, ay = x0 + nx, y0 + ny
            pydirectinput.moveTo(ox_son[0] + ax, ox_son[1] + ay)
            time.sleep(0.15)
            pydirectinput.moveTo(ox_son[0] + ax + 1, ox_son[1] + ay)
            time.sleep(0.45)
            kf = kare_al(h)
            for renkli in (True, False):
                ad = " / ".join(t["yazi"] for t in oku.oku(kf, kutu=(ax - 300, ay - 40, ax + 300, ay + 30),
                                                             olcek=3, renkli=renkli))
                if oku.benzer(ad, anahtar):
                    konumlar = durum_oku().get("npc_konum", {})
                    konumlar[anahtar] = [ax - cx, ay - cy]
                    durum_yaz(npc_konum=konumlar)
                    return kapat_d, (ax, ay, ad)
        return kapat_d, None

    def halkali_noktalar(k, kapat_d):
        """Haritada pembe halkayla isaretlenmis (gorev veren) NPC noktalari: [(ekran_x, ekran_y), ...]"""
        cx, cy = kapat_d
        x0, y0, x1, y1 = cx - 242, cy + 17, cx + 12, cy + 334
        p = k[y0:y1, x0:x1].astype(int)
        yesil = ((p[..., 1] > 180) & (p[..., 0] < 140) & (p[..., 2] < 140)).astype(np.uint8)
        pembe = (p[..., 0] > 175) & (p[..., 0] > p[..., 1] + 30) & (p[..., 0] > p[..., 2] + 30) & (p[..., 1] > 120)
        n, _, ist, mer = cv2.connectedComponentsWithStats(yesil * 255, 8)
        sonuc = []
        for i in range(1, n):
            mx, my = int(mer[i][0]), int(mer[i][1])
            halka = pembe[max(0, my - 11):my + 12, max(0, mx - 11):mx + 12]
            ic = pembe[max(0, my - 3):my + 4, max(0, mx - 3):mx + 4]
            if halka.sum() >= 18 and ic.sum() <= 2:
                if all(abs(x0 + mx - a) > 14 or abs(y0 + my - b) > 14 for a, b in sonuc):
                    sonuc.append((x0 + mx, y0 + my))
        return sonuc

    def halkali_npc_git():
        su_an[0] = "halkali_npc_git"
        """Haritadaki halkali (gorev veren) NPC'lerden yakin zamanda denenmemis olanina gidip konusur."""
        kapat_d = harita_ac()
        if kapat_d is None:
            return False
        k = kare_al(h)
        Image.fromarray(k).save(os.path.join(KLASOR, "goruntu", "harita_halka.png"))
        noktalar = halkali_noktalar(k, kapat_d)
        denemeler = durum_oku().get("halka_deneme", {})
        cx, cy = kapat_d
        for ax, ay in noktalar:
            anahtar_k = f"{(ax - cx) // 4},{(ay - cy) // 4}"
            if time.time() - denemeler.get(anahtar_k, 0) < ayar["npc_tekrar_dk"] * 60:
                continue
            denemeler[anahtar_k] = time.time()
            durum_yaz(halka_deneme=denemeler)
            pydirectinput.moveTo(ox_son[0] + ax, ox_son[1] + ay)
            time.sleep(0.15)
            pydirectinput.moveTo(ox_son[0] + ax + 1, ox_son[1] + ay)
            time.sleep(0.45)
            kf = kare_al(h)
            ad = " / ".join(t["yazi"] for t in oku.oku(kf, kutu=(ax - 300, ay - 40, ax + 300, ay + 30), olcek=3, renkli=True))
            ad_kisa = oku.sade(ad).split("(")[0].strip()[:20]
            print(f"{time.strftime('%H:%M:%S')}  gorev veren npc (haritada halkali): {ad} - yuruyor")

            def yeniden(ax=ax, ay=ay):
                kd = harita_ac()
                if kd is None:
                    return None, None
                return kd, (kd[0] + (ax - cx), kd[1] + (ay - cy), ad)

            sonuc = yuru_ve_konus(kapat_d, (ax, ay, ad), ad_kisa.split(" ")[0] if ad_kisa else "", [], "npc_gorev", yeniden)
            print(f"{time.strftime('%H:%M:%S')}  halkali npc: {'konusuldu' if sonuc else 'olmadi'}")
            return True
        tikla(*kapat_d)
        return False

    GOREV_JSON = os.path.join(KLASOR, "gorev_metinleri.json")

    def gorev_json_oku():
        try:
            with open(GOREV_JSON, encoding="utf-8") as f_:
                d_ = json.load(f_)
            return d_ if isinstance(d_, dict) else {}
        except Exception:
            return {}

    def gorev_json_yaz(d_):
        try:
            gecici_ = GOREV_JSON + ".tmp"
            with open(gecici_, "w", encoding="utf-8") as f_:
                json.dump(d_, f_, ensure_ascii=False, indent=1)
            os.replace(gecici_, GOREV_JSON)
        except Exception as e_:
            print(f"   gorev_json yazilamadi: {e_}")

    def diyalog_kaydet(satirlar):
        """Okunan her NPC diyalogunu (NPC adi + metin) gorev_metinleri.json 'diyaloglar' listesine ekler (son 200). Yalniz kayit."""
        try:
            parcalar_ = [t["yazi"].strip() for t in satirlar if t["yazi"].strip()]
            if not parcalar_:
                return
            npc_ = next((p_.rstrip(":").strip() for p_ in parcalar_ if p_.endswith(":")), "")
            d_ = gorev_json_oku()
            liste_ = d_.setdefault("diyaloglar", [])
            kayit_ = {"zaman": time.strftime("%Y-%m-%d %H:%M:%S"), "npc": npc_, "metin": " ".join(parcalar_)}
            if liste_ and liste_[-1].get("metin") == kayit_["metin"]:
                return
            liste_.append(kayit_)
            del liste_[:-200]
            gorev_json_yaz(d_)
        except Exception:
            pass

    def diyalog_acik(kf, taban):
        """Ortada konusma/gorev penceresi acik mi? (karartma ya da OK/Tamam/Evet yazisi)"""
        yuk_, gen_ = kf.shape[:2]
        satirlar = oku.oku(kf, kutu=(gen_ // 2 - 340, yuk_ * 0.25, gen_ // 2 + 340, yuk_ * 0.8), olcek=3)
        yazi = " ".join(t["yazi"] for t in satirlar)
        if any(oku.sade(w) in oku.sade(yazi).split() for w in ("ok", "tamam", "evet", "kapat", "devam", "hayir", "kabul")):
            return True
        uzun = sum(1 for t in satirlar if len(t["yazi"]) > 18)
        konusan = any(t["yazi"].strip().endswith(":") for t in satirlar)   # "Biyolog Chaegirab:"
        return uzun >= 3 and (konusan or orta_parlaklik(kf) < taban * 0.75)

    def diyalog_ilerlet(tercih, klasor_adi, taban):
        su_an[0] = "diyalog_ilerlet"
        """Acik konusma penceresinde tercih edilen secenege tiklar; yasakli seceneklere dokunmaz.
        Her adimin goruntusu kaydedilir. Donus: tiklanan satirlarin listesi."""
        yasak = ["zihinsel", "hayir", "vazgec", "kapat", "iptal", "close", "cancel"]
        onay = ["evet", "kabul", "onayla", "ogren", "basla", "sec"]        # "al" yok: "Satin Al" dugmesine basmasin
        gec = ["ok", "tamam", "devam", "ileri", "sonraki"]
        dk = os.path.join(KLASOR, "goruntu", klasor_adi)
        os.makedirs(dk, exist_ok=True)
        tiklanan, denenen = [], set()
        for adim in range(12):
            if win32gui.GetForegroundWindow() != h:
                print("   diyalog: oyun penceresi onde degil - birakildi")
                break
            kf = kare_al(h)
            if not diyalog_acik(kf, taban):
                break
            Image.fromarray(kf).save(os.path.join(dk, f"{time.strftime('%H%M%S')}_adim{adim}.png"))
            yuk_, gen_ = kf.shape[:2]
            satirlar = oku.oku(kf, kutu=(gen_ // 2 - 340, yuk_ * 0.2, gen_ // 2 + 340, yuk_ * 0.85), olcek=3)
            print(f"   diyalog adim {adim}:", " | ".join(t["yazi"] for t in satirlar))
            tum_s = oku.sade(" ".join(t["yazi"] for t in satirlar))
            if not any(w in tum_s for w in ("satin al", "nesne market", "fiyat ep", "magaza", "fiyat", "satici")):
                diyalog_kaydet(satirlar)
            if any(w in tum_s for w in ("satin al", "nesne market", "fiyat ep", "ep yukle", " ep ", "markete git", "magaza", "fiyat", "satici", "yere at", "atmak ist", "dusur")):
                print("   KORUMA: satin alma / market penceresi - hicbir seye basilmadi, Esc ile kapatildi")
                for _ in range(3):
                    pydirectinput.press("esc")
                    time.sleep(0.25)
                break
            # gorev yazisi "... Ac Alfa Kurtlardan bulabilirsin" diyorsa o yaratigi aranacaklara ekle
            for m_ in re.finditer(r"((?:[a-z]+ ){0,2}[a-z]{2,}?)l[ae]rd[ae]n (?:bul|al|topla|dus|elde)",
                                  oku.sade(" ".join(t["yazi"] for t in satirlar))):
                kelimeler_ = m_.group(1).split()
                for i_ in range(len(kelimeler_) - 1, -1, -1):       # "bitkisini" gibi nesne ekli kelime ve oncesi ad degil
                    if kelimeler_[i_].endswith(("ni", "nu", "yi", "yu")):
                        kelimeler_ = kelimeler_[i_ + 1:]
                        break
                ad_ = " ".join(kelimeler_)
                if len(ad_.replace(" ", "")) >= 5 and ad_ not in aranan_durum:
                    aranan_durum.append(ad_)
                    del aranan_durum[:-5]
                    durum_yaz(aranan=aranan_durum)
                    print(f"{time.strftime('%H:%M:%S')}  aranan yaratik eklendi: {ad_}")
            kisa = [t for t in satirlar if len(oku.sade(t["yazi"])) <= 34
                    and not any(oku.benzer(t["yazi"], y) for y in yasak)
                    and (oku.sade(t["yazi"]), adim // 2) not in denenen]
            tum = " ".join(t["yazi"] for t in satirlar)
            sec_ = None
            for t in kisa:
                if tercih and any(oku.benzer(t["yazi"], w) for w in tercih):
                    sec_ = t
            if sec_ is None and not oku.benzer(tum, "zihinsel"):
                for t in kisa:
                    if any(oku.sade(w) in oku.sade(t["yazi"]).split() for w in onay):
                        sec_ = t
            if sec_ is None:
                for t in kisa:
                    if any(oku.sade(w) in oku.sade(t["yazi"]).split() for w in gec):
                        sec_ = t
            if sec_ is None and satirlar:                        # kucuk dugme yazisi: alt kismi buyutup yeniden oku
                alt_y = max(t["y1"] for t in satirlar)
                for t in oku.oku(kf, kutu=(gen_ // 2 - 260, alt_y - 10, gen_ // 2 + 260, alt_y + 90), olcek=5):
                    if any(oku.sade(w) in oku.sade(t["yazi"]).split() for w in gec + onay):
                        sec_ = t
                        break
            if sec_ is None:
                print("   diyalog: tanidik dugme yok - pencere kapatildi")
                pydirectinput.press("esc")
                break
            else:
                denenen.add((oku.sade(sec_["yazi"]), adim // 2))
                tiklanan.append(sec_["yazi"])
                print("   diyalog: tiklandi ->", sec_["yazi"])
                tikla(sec_["x"], sec_["y"])
            time.sleep(0.7)
            pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
        return tiklanan

    def npc_tikla_dene(kf, aday, ek, taban, tercih, klasor_adi):
        """Bir isim etiketinin altina tiklayip konusma penceresi acilir mi dener."""
        for alt in (55, 85, 30, 120):
            tikla(aday["x"], aday["y"] + alt)
            time.sleep(1.8)
            kd = kare_al(h)
            if diyalog_acik(kd, taban):
                print(f"   npc: konusma acildi ({aday['yazi']})")
                diyalog_ilerlet(tercih, klasor_adi, taban)
                return True
        return False

    def npc_git(anahtar, tercih, klasor_adi):
        """Haritadan NPC'yi adiyla bulur, oraya yurur ve konusur."""
        kapat_d, hedef = harita_npc_bul(anahtar)
        if hedef is None:
            print(f"npc: haritada '{anahtar}' bulunamadi")
            if kapat_d:
                tikla(*kapat_d)
            return False
        print(f"{time.strftime('%H:%M:%S')}  npc: '{anahtar}' haritada bulundu, yuruyor")
        return yuru_ve_konus(kapat_d, hedef, anahtar, tercih, klasor_adi, lambda: harita_npc_bul(anahtar))

    yol_yigin_dosya = os.path.join(KLASOR, "goruntu", "harita_yigin.npy")
    yol_d = {"yigin": []}
    try:
        yol_d["yigin"] = list(np.load(yol_yigin_dosya))
    except Exception:
        pass

    def harita_yuru(kapat_d, hx, hy, ust_sure=180, dur_kosulu=None):
        su_an[0] = "harita_yuru"
        """Acik haritada (hx, hy) ekran noktasina YOLDAN yurur: harita resminden su/kaya/yol okunur, rota
        bulunur, aralarinda engel olmayan duraklara sirayla tiklanir (oyun tek tikta dumduz yurutuyor).
        Donus: True vardi | False varamadi / yarida kesildi / rota yok | None oyuncunun yeri bilinmiyor
        (cagiran eski usul tek tikla yurutur). Harita acik birakilir; kapatmak cagiranin isi."""
        cx, cy = kapat_d
        x0, y0 = cx - 242, cy + 17

        def harita_karesi():
            k_ = kare_al(h)
            return k_, k_[y0:y0 + 317, x0:x0 + 254]

        pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)   # imlec/ipucu haritayi ortmesin
        time.sleep(0.25)
        k_, p_ = harita_karesi()
        if p_.shape[:2] != (317, 254):
            return None
        yol_d["yigin"], arka = yolbul.arka_guncelle(yol_d["yigin"], p_)
        try:
            np.save(yol_yigin_dosya, np.stack(yol_d["yigin"]))
        except Exception:
            pass
        oyuncu = yolbul.oyuncu_bul(p_, arka)
        if oyuncu is None:
            print(f"   yol: haritada kendi yerim bulunamadi ({len(yol_d['yigin'])} kare) - duz yuruyus")
            return None
        sinif = yolbul.siniflandir(arka)
        m_ = yolbul.maliyet_izgarasi(sinif)
        qa_ = arka.astype(int)                              # koy alani pahali: rota koyun icinden gecmesin
        npca_ = ((qa_[..., 1] > 180) & (qa_[..., 0] < 140) & (qa_[..., 2] < 140)).astype(np.uint8)
        koy_m = cv2.dilate(npca_, np.ones((31, 31), np.uint8)) > 0
        m_[koy_m & np.isfinite(m_)] += 25
        rota = yolbul.yol_bul(m_, oyuncu, (hx - x0, hy - y0))
        if not rota:
            print("   yol: hedefe gecilir rota yok (su/kaya ile ayrilmis) - vazgecildi")
            return False
        durak = yolbul.duraklar(m_, rota)
        try:
            Image.fromarray(yolbul.ciz(arka, sinif, rota, durak, oyuncu)).save(os.path.join(KLASOR, "goruntu", "yol_son.png"))
        except Exception:
            pass
        print(f"   yol: {len(rota)} piksellik rota, {len(durak)} durak")
        bas = time.time()
        for i, (dx_, dy_) in enumerate(durak):
            tikla(x0 + dx_, y0 + dy_)
            pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
            gecmis_k, yeniden, durak_bas, kayip_bas = [], 0, time.time(), None
            while True:
                if time.time() - bas > ust_sure or not durum["calis"] or durum["duraklat"]:
                    return False
                if time.time() - durak_bas > 15:
                    print(f"   yol: {i + 1}. duraga 15 sn'de varilamadi - yolculuk birakildi")
                    return False
                time.sleep(0.45)
                if win32gui.GetForegroundWindow() != h:
                    continue
                k_, p_ = harita_karesi()
                if olum_denetle(k_):
                    return False
                can_ = can_orani(k_)
                if 0.02 <= can_ < ayar["can_esigi"]:
                    pydirectinput.press(ayar["can_potu_tusu"])
                if 0.02 <= can_ < ayar["yolda_saldiri_can"]:
                    print("   yol: yolda saldiriya ugradi - yolculuk birakildi")
                    return False
                if dur_kosulu is not None and dur_kosulu(k_):
                    tikla(k_.shape[1] // 2, int(k_.shape[0] * 0.58))     # dur
                    return False
                konum = yolbul.oyuncu_bul(p_, arka)
                simdi_k = time.time()
                if konum is None:
                    kayip_bas = kayip_bas or simdi_k
                    if simdi_k - kayip_bas > 2.5:
                        print("   yol: haritada yerim kayboldu - yolculuk birakildi")
                        return False
                    continue
                kayip_bas = None
                if math.hypot(konum[0] - dx_, konum[1] - dy_) <= 2.0:
                    break                                           # duraga varildi
                gecmis_k.append((simdi_k, konum))
                eski_k = [g for g in gecmis_k if simdi_k - g[0] >= 1.5]
                if eski_k and math.hypot(konum[0] - eski_k[-1][1][0], konum[1] - eski_k[-1][1][1]) < 1.0:
                    if yeniden >= 2:
                        print(f"   yol: {i + 1}. durakta takildi (2 kez yana kacildi) - yolculuk birakildi")
                        return False
                    yeniden, gecmis_k = yeniden + 1, []
                    gen_y, yuk_y = k_.shape[1], k_.shape[0]
                    kx_y, ky_y = gen_y // 2, int(yuk_y * 0.58)
                    yan = -1 if yeniden == 1 else 1
                    yx, yy_ = bos_yon(k_, math.atan2(150, yan * 230))
                    if x0 - 20 < yx < x0 + 274 and y0 - 40 < yy_ < y0 + 340:      # haritanin ustune tiklama
                        yx = kx_y - yan * 230
                    tikla(yx, yy_)                                   # engelden yana kac
                    time.sleep(0.8)
                    tikla(x0 + dx_, y0 + dy_)                        # ayni duraga devam
                    pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
                gecmis_k = [g for g in gecmis_k if simdi_k - g[0] < 6]
        return True

    def yuru_ve_konus(kapat_d, hedef, anahtar, tercih, klasor_adi, yeniden_bul):
        su_an[0] = "yuru_ve_konus"
        """Haritadaki noktaya yurur; varinca adi tutan (yoksa en yakin, kirmizi olmayan)
        isim etiketine tiklar ve konusmayi ilerletir."""
        hx, hy, ad = hedef
        yoldan = harita_yuru(kapat_d, hx, hy)                   # yoldan, ara duraklarla
        if yoldan is None:
            tikla(hx, hy)                                       # yerim bilinmiyor: eski usul duz yuruyus
            time.sleep(0.5)
        tikla(*kapat_d)
        if yoldan is False:
            return False
        pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
        ek = os.path.join(KLASOR, "goruntu", klasor_adi)
        os.makedirs(ek, exist_ok=True)
        onceki, durgun, bas, yeniden_yuru = None, 0, time.time(), 0
        while time.time() - bas < 180 and durum["calis"] and not durum["duraklat"]:
            time.sleep(1.0)
            if win32gui.GetForegroundWindow() != h:
                continue
            kf = kare_al(h)
            if olum_denetle(kf):
                return False
            can_simdi = can_orani(kf)
            if can_simdi < ayar["can_esigi"]:
                pydirectinput.press(ayar["can_potu_tusu"])
            if can_simdi < ayar["yolda_saldiri_can"]:
                print("   npc: yolda saldiriya ugradi - yolculuk birakildi")
                return False
            mh, _ = mini_harita(kf)
            if onceki is not None:
                durgun = durgun + 1 if float(np.abs(mh - onceki).mean()) < 0.6 else 0
            onceki = mh
            if durgun < 3:
                continue
            # vardi (mini harita duruyor): etiketleri oku
            yuk_, gen_ = kf.shape[:2]
            Image.fromarray(kf).save(os.path.join(ek, f"{time.strftime('%H%M%S')}_varis.png"))
            etiketler = oku.oku(kf, kutu=(gen_ // 2 - 700, 60, gen_ // 2 + 700, yuk_ - 180), olcek=3, renkli=True)
            print("   npc: varista gorulen etiketler:", " | ".join(t["yazi"] for t in etiketler))
            taban = orta_parlaklik(kf)
            kx, ky = gen_ // 2, int(yuk_ * 0.45)
            adlar = ayar["npc_adlari"].get(anahtar, [anahtar]) if anahtar else []
            tutan = [t for t in etiketler if any(a_ and oku.benzer(t["yazi"], a_) for a_ in adlar)]
            for ux, uy, ub in gorev_ucgenleri(kf):            # ucgenin altinda once ad, sonra govde
                tutan.insert(0, {"yazi": "gorev isareti", "x": ux, "y": uy + ub * 3})
            kirmizi = kirmizi_etiketler(kf)

            def kirmizi_mi(t):
                return any(abs(t["x"] - q[0]) < 120 and abs(t["y"] - (q[1] - 6)) < 14 for q in kirmizi)

            digerleri = [t for t in etiketler if t not in tutan and not kirmizi_mi(t)
                         and not oku.benzer(t["yazi"], "samricke") and math.hypot(t["x"] - kx, t["y"] - ky) > 40
                         and not oku.sade(t["yazi"]).startswith(("lv", "lu", "lu ")) and not oku.benzer(t["yazi"], "arkadas")
                         and len(oku.sade(t["yazi"]).replace(" ", "")) >= 5]
            digerleri.sort(key=lambda t: math.hypot(t["x"] - kx, t["y"] - ky))
            for aday in tutan + digerleri[:3]:
                if npc_tikla_dene(kf, aday, ek, taban, tercih, klasor_adi):
                    return True
            Image.fromarray(kare_al(h)).save(os.path.join(ek, f"{time.strftime('%H%M%S')}_acilmadi.png"))
            if yeniden_yuru < 1:                                 # bir kez daha haritadan yaklas
                yeniden_yuru += 1
                durgun, onceki = 0, None
                kapat_d, hedef = yeniden_bul()
                if hedef and kapat_d:
                    tikla(hedef[0], hedef[1])
                    time.sleep(0.5)
                if kapat_d:
                    tikla(*kapat_d)
                pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
                continue
            print("   npc: yanina gelindi ama konusma acilamadi")
            return False
        return False

    def bolge_sec(kapat_d, aday):
        """Gidilecek cayir noktasi (yy, xx): once seviyeme uygun yaratik gordugum bolge, yoksa hic gitmedigim
        en yakin bolgelerden biri; dusuk/yuksek seviyeli oldugunu bildigim bolgeye gitmem.
        Bulundugum bolgeye son 90 sn'de gordugum yaratik seviyelerinin ortancasi yazilir (durum.json: bolge_sev)."""
        rastgele = tuple(aday[random.randrange(len(aday))])
        try:
            cx, cy = kapat_d
            p_ = kare_al(h)[cy + 17:cy + 334, cx - 242:cx + 12]
            if len(yol_d["yigin"]) < 3:
                return rastgele
            ben = yolbul.oyuncu_bul(p_, np.median(np.stack(yol_d["yigin"]), axis=0).astype(np.uint8))
            if ben is None:
                return rastgele
            H = 24                                              # bolge karesi (harita pikseli)
            bolge = durum_oku().get("bolge_sev", {})
            benim_b = f"{ben[0] // H},{ben[1] // H}"
            simdi = [s_ for z_, s_ in sev_gorulen if time.time() - z_ < 90]
            if len(simdi) >= 3:
                bolge[benim_b] = [float(np.median(simdi)), time.time()]
                durum_yaz(bolge_sev=bolge)
            b_yog = durum_oku().get("bolge_yog", {})
            yog_simdi = [n_ for z_, n_ in yog_gorulen if time.time() - z_ < 90]
            if yog_simdi:
                b_yog[benim_b] = max(yog_simdi)
                durum_yaz(bolge_yog=b_yog)
            b_ad = durum_oku().get("bolge_ad", {})
            adlar_simdi = sorted({a_ for z_, a_ in ad_gorulen if time.time() - z_ < 120})
            if adlar_simdi:
                b_ad[benim_b] = (adlar_simdi + [a_ for a_ in b_ad.get(benim_b, []) if a_ not in adlar_simdi])[:10]
                durum_yaz(bolge_ad=b_ad)
            q0_ = p_.astype(int)
            npc0_ = ((q0_[..., 1] > 180) & (q0_[..., 0] < 140) & (q0_[..., 2] < 140)).astype(np.uint8)
            n0_, _, ist0_, mer0_ = cv2.connectedComponentsWithStats(cv2.dilate(npc0_, np.ones((25, 25), np.uint8)), 8)
            koy0_ = tuple(mer0_[1 + int(np.argmax(ist0_[1:, 4]))]) if n0_ > 1 else None
            if koy0_ is not None:                # koye donus kapali: koy merkezine 45 px'ten yakin hedef yok
                uzak0 = [q for q in aday if math.hypot(q[1] - koy0_[0], q[0] - koy0_[1]) > 45]
                if uzak0:
                    aday = np.array(uzak0)
                    rastgele = tuple(aday[random.randrange(len(aday))])
            odak_ = list(ayar["sadece_hedefler"]) + esya_hedef + (av_aranan if ayar["av_gorevi"] else [])
            if odak_:
                av_b = [k_ for k_, v_ in b_ad.items()
                        if k_ != benim_b and any(oku.benzer(a_, o_, 0.85) for a_ in v_ for o_ in odak_)]
                ic = [(int(yy), int(xx)) for yy, xx in aday[::3] if f"{xx // H},{yy // H}" in av_b]
                if ic:
                    secim = min(ic, key=lambda q: math.hypot(q[1] - ben[0], q[0] - ben[1]))
                    print(f"   bolge: aranan yaratigin ({', '.join(odak_[:3])}) goruldugu bolgeye")
                    return secim
            if not benim_sev:
                return rastgele
            alt_, ust_ = benim_sev - ayar["seviye_alt_fark"], benim_sev + ayar["seviye_ust_fark"]
            q_ = p_.astype(int)
            npc_ = ((q_[..., 1] > 180) & (q_[..., 0] < 140) & (q_[..., 2] < 140)).astype(np.uint8)
            n_k, _, ist_k, mer_k = cv2.connectedComponentsWithStats(cv2.dilate(npc_, np.ones((25, 25), np.uint8)), 8)
            koy_ = tuple(mer_k[1 + int(np.argmax(ist_k[1:, 4]))]) if n_k > 1 else (float(ben[0]), float(ben[1]))
            ben_kd = math.hypot(ben[0] - koy_[0], ben[1] - koy_[1])      # koye uzakligim
            burasi = bolge.get(benim_b, [None])[0]
            iceri = False                       # koye donus kapali (Vedat): hep disari ya da yana
            uzak_aday = [q for q in aday if math.hypot(q[1] - koy_[0], q[0] - koy_[1]) > 45]
            if uzak_aday:
                aday = np.array(uzak_aday)
            uygun, bilinmeyen = [], []
            for yy, xx in aday[::5]:
                a_ = f"{xx // H},{yy // H}"
                if a_ == benim_b:
                    continue
                uz = math.hypot(xx - ben[0], yy - ben[1])
                tablo_uygun = any(alt_ <= bilgi["canavar_lv"].get(" ".join(oku.sade(n_).split()), -99) <= ust_
                                  for n_ in b_ad.get(a_, []))
                if tablo_uygun:
                    uygun.append((uz, int(yy), int(xx)))
                elif a_ in bolge:
                    if alt_ <= bolge[a_][0] <= ust_:
                        uygun.append((uz, int(yy), int(xx)))
                else:
                    bilinmeyen.append((uz, int(yy), int(xx), math.hypot(xx - koy_[0], yy - koy_[1])))
            if not benim_sev:
                return rastgele
            # mini haritadaki kirmizi nokta kumeleri (canlı canavar yogunlugu): disari (ya da iceri) yondeki en kalabalik
            k_m = kare_al(h)
            mm = k_m[30:140, k_m.shape[1] - 140:k_m.shape[1] - 30].astype(int)
            kir_m = ((mm[..., 0] > 140) & (mm[..., 1] < 90) & (mm[..., 2] < 90)).astype(np.uint8)
            kir_m[50:61, 50:61] = 0
            n_m, et_m, ist_m, mer_m = cv2.connectedComponentsWithStats(cv2.dilate(kir_m, np.ones((9, 9), np.uint8)), 8)
            kume_ = None
            dis_x, dis_y = ben[0] - koy_[0], ben[1] - koy_[1]
            for i_m in range(1, n_m):
                agirlik = int(kir_m[et_m == i_m].sum())
                vx, vy = mer_m[i_m][0] - 55, mer_m[i_m][1] - 55
                boy_ = math.hypot(vx, vy) or 1.0
                yon_ok = (vx * dis_x + vy * dis_y) * (-1 if iceri else 1) >= 0 or ben_kd < 8
                if agirlik >= 12 and yon_ok and (kume_ is None or agirlik > kume_[0]):
                    kume_ = (agirlik, vx / boy_, vy / boy_)
            if uygun:
                uygun.sort(key=lambda u_: (-b_yog.get(f"{u_[2] // H},{u_[1] // H}", 0), u_[0]))
                secim = uygun[0]
                a_s = f"{secim[2] // H},{secim[1] // H}"
                print(f"   bolge: seviyeme uygun bilinen bolgeye ({', '.join(b_ad.get(a_s, [])[:3]) or 'ortanca Lv %.0f' % bolge[a_s][0]})")
            elif kume_ is not None:
                hx_, hy_ = ben[0] + kume_[1] * 16, ben[1] + kume_[2] * 16
                yy_k, xx_k = min(((int(a1), int(a2)) for a1, a2 in aday[::3]), key=lambda q: math.hypot(q[1] - hx_, q[0] - hy_))
                print(f"   bolge: mini haritada kalabalik canavar kumesi ({kume_[0]} px kirmizi) yonune")
                return yy_k, xx_k
            elif bilinmeyen:
                yon_ = [b_ for b_ in bilinmeyen if (b_[3] < ben_kd - 10 if iceri else b_[3] > ben_kd + 10)]
                havuz = yon_ or bilinmeyen
                havuz.sort()
                secim = random.choice(havuz[:max(1, len(havuz) // 4)])
                print(f"   bolge: henuz bakilmamis bolgeye {'ICERI' if iceri else 'DISARI'}: koyden {ben_kd:.0f} -> "
                      f"{secim[3]:.0f} px ({len(bolge)} bolge biliniyor)")
            else:
                return rastgele
            return secim[1], secim[2]
        except Exception as e_:
            print("bolge_sec:", e_)
            return rastgele

    gez_yon = [random.uniform(0, 2 * math.pi)]       # son yurunen yon (momentum)

    def sari_maske(x):
        x = x.astype(int)
        return (((x[..., 0] > 170) & (x[..., 1] > 150) & (x[..., 2] < 150) & (x[..., 0] - x[..., 2] > 60)) * 255).astype(np.uint8)

    _yol_sen = os.path.join(KLASOR, "sablon", "sen.png")
    sen_sab = sari_maske(cv2.cvtColor(cv2.imread(_yol_sen), cv2.COLOR_BGR2RGB)) if os.path.exists(_yol_sen) else None

    def mini_kume_yonu(k):
        """Mini haritadaki en kalabalik kirmizi nokta kumesinin yonu (aci, agirlik) ya da None."""
        mm = k[30:140, k.shape[1] - 140:k.shape[1] - 30].astype(int)
        kir_m = ((mm[..., 0] > 140) & (mm[..., 1] < 90) & (mm[..., 2] < 90)).astype(np.uint8)
        kir_m[48:63, 48:63] = 0
        n_m, et_m, _, mer_m = cv2.connectedComponentsWithStats(cv2.dilate(kir_m, np.ones((9, 9), np.uint8)), 8)
        kumeler = []
        for i_m in range(1, n_m):
            agirlik = int(kir_m[et_m == i_m].sum())
            if agirlik >= 12:
                kumeler.append((agirlik, math.atan2(mer_m[i_m][1] - 55, mer_m[i_m][0] - 55)))
        return sorted(kumeler, reverse=True)

    def gezin_buyuk():
        """Oyunun Buyuk haritasindan yuru. Donus: True yurudu / False olmadi (eski gezinmeye dus)."""
        su_an[0] = "gezin_buyuk"
        k0 = kare_al(h)
        kumeler = mini_kume_yonu(k0)
        pencereleri_kapat()
        once = acik_pencereler(kare_al(h), kapat_s)
        pydirectinput.press("m")
        genel = None
        for _ in range(10):
            time.sleep(0.12)
            yeni_ = [q for q in acik_pencereler(kare_al(h), kapat_s) if all(abs(q[0] - o[0]) > 6 or abs(q[1] - o[1]) > 6 for o in once)]
            if yeni_:
                genel = yeni_[0]
                break
        if genel is None:
            return False
        kg = kare_al(h)
        dugme = [t for t in oku.oku(kg, kutu=(genel[0] - 300, genel[1] + 300, genel[0] + 40, genel[1] + 400), olcek=3)
                 if oku.benzer(t["yazi"], "buyuk harita", 0.75)]
        if not dugme:
            pydirectinput.press("esc")
            return False
        tikla(dugme[0]["x"], dugme[0]["y"])
        buyuk = None
        for _ in range(12):
            time.sleep(0.12)
            for q in acik_pencereler(kare_al(h), kapat_s):
                if abs(q[0] - genel[0]) > 20 and q[1] < genel[1] + 40 and q[0] > 900:   # genel haritanin yerine acilan buyuk harita
                    buyuk = q
            if buyuk:
                break
        if buyuk is None:
            pydirectinput.press("esc")
            return False
        pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
        time.sleep(0.2)
        kb = kare_al(h)
        bx, by = buyuk
        x0b, x1b, y0b, y1b = bx - 899, bx - 300, by + 25, by + 549          # harita alani (X dugmesine gore)
        sen = []
        if sen_sab is not None:                           # sari "Sen" yazisi (maske sablonu; acik zeminde de)
            r_s = cv2.matchTemplate(sari_maske(kb[y0b:y1b, x0b:x1b]), sen_sab, cv2.TM_CCOEFF_NORMED)
            _, v_s, _, l_s = cv2.minMaxLoc(r_s)
            if v_s >= 0.6:
                sen = [{"x0": x0b + l_s[0], "y": y0b + l_s[1] + 8}]
        if not sen:
            sen = [t for t in oku.oku(kb, kutu=(x0b, y0b, x1b, y1b), olcek=2)
                   if " ".join(oku.sade(t["yazi"]).split()) == "sen"]
        if not sen:
            Image.fromarray(kb).save(os.path.join(KLASOR, "goruntu", "buyuk_harita_sen_yok.png"))
            print("   gezin: buyuk haritada 'Sen' bulunamadi")
            tikla(bx, by)
            return False
        sx, sy = sen[0]["x0"] - 20, sen[0]["y"]
        # koy yonu: haritadaki NPC noktalari (yesil) yeterince varsa ortalamalari
        q_ = kb[y0b:y1b, x0b:x1b].astype(int)
        npc_ = ((q_[..., 1] > 180) & (q_[..., 0] < 140) & (q_[..., 2] < 140)).astype(np.uint8)
        n_, _, ist_, mer_ = cv2.connectedComponentsWithStats(npc_, 8)
        noktalar = [(mer_[i][0] + x0b, mer_[i][1] + y0b) for i in range(1, n_) if ist_[i][4] >= 3]
        koy_aci = (math.atan2(np.mean([p_[1] for p_ in noktalar]) - sy, np.mean([p_[0] for p_ in noktalar]) - sx)
                   if len(noktalar) >= 4 else None)

        def koye_mi(a):
            return koy_aci is not None and abs((a - koy_aci + math.pi) % (2 * math.pi) - math.pi) < math.radians(70)

        aci, neden = None, ""
        for agirlik, a in kumeler:
            if not koye_mi(a):
                aci, neden = a, f"mini haritadaki canavar kumesi ({agirlik})"
                break
        if aci is None:
            a = gez_yon[0] + random.uniform(-0.5, 0.5)
            if koye_mi(a):
                a += math.pi
            aci, neden = a, "onceki yonde devam"
        gez_yon[0] = aci
        print(f"{time.strftime('%H:%M:%S')}  gezin: buyuk haritadan {neden} yonune ({math.degrees(aci):.0f} derece)")
        yurudu = False
        for deneme, (sapma, R) in enumerate(((0, 110), (0.7, 100), (-0.7, 100), (0, 60))):
            a_d = aci + sapma
            hx = min(max(sx + R * math.cos(a_d), x0b + 40), x1b - 60)    # kenar ve sag ustteki +/- dugmelerinden uzak
            hy = min(max(sy + R * math.sin(a_d), y0b + 40), y1b - 40)
            mh0, _ = mini_harita(kare_al(h))
            tikla(hx, hy)                                      # oyun engellerden kacarak kendisi yurur
            pydirectinput.moveTo(ox_son[0] + kb.shape[1] // 2, ox_son[1] + int(kb.shape[0] * 0.93))
            for _ in range(4):
                time.sleep(0.3)
                if float(np.abs(mini_harita(kare_al(h))[0] - mh0).mean()) > 1.5:
                    yurudu = True
                    break
            if yurudu:
                gez_yon[0] = a_d
                break
        if not yurudu:
            print("   gezin: haritada tiklanan 4 noktaya da yurunemedi")
            gez_yon[0] += math.pi / 2
            tikla(bx, by)
            return True
        pydirectinput.moveTo(ox_son[0] + kb.shape[1] // 2, ox_son[1] + int(kb.shape[0] * 0.93))
        harita_acik = [True]                                   # yuruyus boyunca harita acik kalir (kapatmak yuruyusu kesebilir)

        def kapat_harita():
            if harita_acik[0]:
                harita_acik[0] = False
                tikla(bx, by)
                pydirectinput.moveTo(ox_son[0] + kb.shape[1] // 2, ox_son[1] + int(kb.shape[0] * 0.8))
        kapat_harita()                       # yuruyus basladi; harita kapaninca da devam ediyor (17.11 olculdu) - slotlar gorunsun
        bas, onceki, durgun = time.time(), None, 0
        hz_ = hizli_baslat()
        while time.time() - bas < 25 and durum["calis"] and not durum["duraklat"]:
            time.sleep(0.4)
            kf = kare_al(h)
            if olum_denetle(kf):
                kapat_harita()
                return True
            can_ = can_orani(kf)
            if 0.02 <= can_ < ayar["can_esigi"]:
                pydirectinput.press(ayar["can_potu_tusu"])
            if 0.02 <= can_ < ayar["yolda_saldiri_can"]:
                kapat_harita()
                return True                                    # saldiri var: kesmeye don
            tum = kirmizi_etiketler(kf)
            if ayar["sadece_hedefler"]:
                gordu = bool(sadece_suz(kf, tum))              # yalniz secilen canavar gorununce dur
            else:
                gordu = (sum(1 for t in tum for u in tum if math.hypot(t[0] - u[0], t[1] - u[1]) < ayar["slot_yaricapi_piksel"]) >= 6
                         or (ayar["metin_kes"] and bool(beyaz_etiketler(kf))))
            if gordu:
                kapat_harita()
                return True                                    # slot gorundu: ana dongu hemen hedef secer
            if hizli_adim(hz_, kf):
                onceki, durgun = None, 0
                continue
            mh, _ = mini_harita(kf)
            if onceki is not None:
                durgun = durgun + 1 if float(np.abs(mh - onceki).mean()) < 0.6 else 0
                if durgun >= 5:                                # ~2 sn kipirdamadi: vardi ya da yol yok
                    if time.time() - bas < 3:
                        gez_yon[0] += math.pi / 2              # hic yuruyemedi: sonraki sefer baska yon
                    kapat_harita()
                    return True
            onceki = mh
        kapat_harita()
        return True

    alan = {"yerel": 0, "aci": random.uniform(0, 2 * math.pi)}

    def alan_ici_yuru():
        """Harita acmadan kisa yuruyus: yere tik (karakterin 250-330 px otesi), 1.6 sn boyunca hedef gorunurse dur."""
        su_an[0] = "alan ici kisa yuruyus"
        k_ = kare_al(h)
        yk_, gn_ = k_.shape[:2]
        kx_, ky_ = gn_ // 2, int(yk_ * 0.58)
        alan["aci"] += random.choice((-1, 1)) * random.uniform(math.radians(60), math.radians(120))
        r_ = random.uniform(250, 330)
        tx = min(max(kx_ + r_ * math.cos(alan["aci"]), 320), gn_ - 320)          # sol alt / sag ust arayuzden uzak
        ty = min(max(ky_ + r_ * 0.6 * math.sin(alan["aci"]), yk_ * 0.25), yk_ * 0.8)
        birak()
        tikla(tx, ty)
        pydirectinput.moveTo(ox_son[0] + kx_, ox_son[1] + int(yk_ * 0.9))
        bas_ = time.time()
        hz_ = hizli_baslat(alan["aci"], (tx, ty))
        while time.time() - bas_ < (2.2 if ayar.get("hizli_engel", True) else 1.6) and durum["calis"] and not durum["duraklat"]:
            time.sleep(0.2)
            kf_ = kare_al(h)
            tum_ = kirmizi_etiketler(kf_)
            if ayar["sadece_hedefler"]:
                if sadece_suz(kf_, tum_):
                    return
            elif sum(1 for t in tum_ for u in tum_ if math.hypot(t[0] - u[0], t[1] - u[1]) < ayar["slot_yaricapi_piksel"]) >= 6:
                return
            if not saldiri_altinda():
                hizli_adim(hz_, kf_)

    def mini_harita_yuru():
        """Buyuk haritayi acmadan: mini haritadaki en yakin kirmizi nokta kumesine dogru ekranda bos yone yuru.
        Hedef etiketi gorunurse durur. Donus: True yurundu (kume vardi), False kume yok."""
        try:
            k_ = kare_al(h)
            mm = k_[30:140, k_.shape[1] - 140:k_.shape[1] - 30].astype(int)
            kir_m = ((mm[..., 0] > 140) & (mm[..., 1] < 90) & (mm[..., 2] < 90)).astype(np.uint8)
            kir_m[48:63, 48:63] = 0
            n_m, et_m, _, mer_m = cv2.connectedComponentsWithStats(cv2.dilate(kir_m, np.ones((9, 9), np.uint8)), 8)
            en = None
            for i_m in range(1, n_m):
                ag = int(kir_m[et_m == i_m].sum())
                if ag < max(12, 4 * ayar["slot_en_az"]):
                    continue
                vx, vy = mer_m[i_m][0] - 55, mer_m[i_m][1] - 55
                uz = math.hypot(vx, vy)
                if en is None or uz < en[0]:
                    en = (uz, ag, math.atan2(vy, vx))
            if en is None:
                return False
            su_an[0] = "mini harita: kumeye yuruyor"
            print(f"{time.strftime('%H:%M:%S')}  mini harita: kumeye yuruyor ({en[1]} px kirmizi, {en[0]:.0f} px uzakta, {math.degrees(en[2]):.0f} derece)")
            tx, ty = bos_yon(k_, en[2], rx=330, ry=210)
            birak()
            tikla(tx, ty)
            pydirectinput.moveTo(ox_son[0] + k_.shape[1] // 2, ox_son[1] + int(k_.shape[0] * 0.9))
            bas_ = time.time()
            hz_ = hizli_baslat(en[2], (tx, ty))
            while time.time() - bas_ < 2.2 and durum["calis"] and not durum["duraklat"]:
                time.sleep(0.2)
                kf_ = kare_al(h)
                tum_ = kirmizi_etiketler(kf_)
                if ayar["sadece_hedefler"]:
                    if sadece_suz(kf_, tum_):
                        break
                elif sum(1 for t in tum_ for u in tum_ if math.hypot(t[0] - u[0], t[1] - u[1]) < ayar["slot_yaricapi_piksel"]) >= 6:
                    break
                if not saldiri_altinda():
                    hizli_adim(hz_, kf_)
            return True
        except Exception as e_:
            print("mini_harita_yuru:", e_)
            return False

    alan_mola = [0.0, 0]   # [alan modunun askida oldugu son an, ust uste basarisiz alan yuruyusu]

    def alan_aktif():
        """Alan secenegi acik ve alan modu askida degil (harita acilamayinca / baska haritadaysa askiya alinir)."""
        return bool(ayar.get("kasilma_alani") and ayar.get("alan_kullan")) and time.time() > alan_mola[0]

    engel_dosya = os.path.join(KLASOR, "engeller.json")
    engel_h = {"veri": None, "son": 0.0}

    def engel_veri():
        if engel_h["veri"] is None:
            try:
                with open(engel_dosya, encoding="utf-8") as f_:
                    engel_h["veri"] = json.load(f_)
            except Exception:
                engel_h["veri"] = {}
        return engel_h["veri"]

    def engel_noktalari(ad):
        """Kayitli takilma noktalari [(x, y, sayi)] (ad bos/bilinmiyorsa tum haritalar)."""
        if not ayar.get("engel_hafiza", True):
            return []
        out_ = []
        for k_, liste_ in engel_veri().items():
            if not ad or k_ == "?" or oku.sade(k_) == oku.sade(ad):
                out_ += [(e_[0], e_[1], e_[3]) for e_ in liste_]
        return out_

    def engel_yakin(ad, x, y):
        for ex_, ey_, say_ in engel_noktalari(ad):
            if math.hypot(x - ex_, y - ey_) < (0.03 if say_ >= 2 else 0.02):
                return True
        return False

    def engel_kaydet(neden):
        """Gercek takilmada genel haritadan kendi konumumu okuyup engeller.json'a yazar (en cok 60 sn'de bir)."""
        if not ayar.get("engel_hafiza", True) or time.time() - engel_h["son"] < 60 or saldiri_altinda():
            return
        engel_h["son"] = time.time()
        t0_ = time.time()
        g_ = genel_harita_resmi()
        if g_ is None:
            return
        kd_, resim, _, _ = g_
        try:
            if resim.shape[:2] != (317, 254):
                return
            ad_ = kayitli_harita_bul(resim) or "?"
            yol_d["yigin"], arka_ = yolbul.arka_guncelle(yol_d["yigin"], resim)
            oy_ = yolbul.oyuncu_bul(resim, arka_)
        finally:
            tikla(*kd_)
        if oy_ is None:
            print(f"{time.strftime('%H:%M:%S')}  engel hafiza: haritada yerim bulunamadi ({time.time() - t0_:.1f} sn)")
            return
        x_, y_ = round(float(oy_[0]) / 254, 4), round(float(oy_[1]) / 317, 4)
        liste_ = engel_veri().setdefault(ad_, [])
        for e_ in liste_:
            if math.hypot(e_[0] - x_, e_[1] - y_) < 0.01:
                e_[2], e_[3] = int(time.time()), e_[3] + 1
                sayi_ = e_[3]
                break
        else:
            liste_.append([x_, y_, int(time.time()), 1])
            sayi_ = 1
        try:
            with open(engel_dosya + ".tmp", "w", encoding="utf-8") as f_:
                json.dump(engel_veri(), f_, ensure_ascii=False)
            os.replace(engel_dosya + ".tmp", engel_dosya)
        except Exception as e_w:
            print("engel hafiza yazilamadi:", e_w)
        print(f"{time.strftime('%H:%M:%S')}  engel hafiza: kaydedildi {ad_} ({x_}, {y_}) sayi={sayi_} [{neden}] - harita okuma {time.time() - t0_:.1f} sn")

    def alan_noktasi():
        """Cizilen kasilma alaninin icinde rastgele bir nokta (oran olarak); kayitli engel noktalarindan uzak."""
        a_ = ayar["kasilma_alani"]
        for _ in range(40):
            aci_, r_ = random.uniform(0, 2 * math.pi), a_["r"] * math.sqrt(random.uniform(0.05, 1.0))
            x_, y_ = a_["x"] + r_ * math.cos(aci_), a_["y"] + r_ * math.sin(aci_) * 254 / 317
            if 0.02 < x_ < 0.98 and 0.02 < y_ < 0.98:
                if engel_yakin(a_.get("harita", ""), x_, y_):
                    continue
                return round(x_, 4), round(y_, 4)
        return a_["x"], a_["y"]

    def gezin():
        su_an[0] = "gezin"
        son_gezin[0] = time.time()
        if alan_aktif():   # secenek acik: yalniz cizilen alanda dolas
            x_, y_ = alan_noktasi()
            print(f"{time.strftime('%H:%M:%S')}  alan: cizilen kasilma alaninin icinde yeni noktaya ({x_}, {y_})")
            try:
                if harita_git(ayar["kasilma_alani"].get("harita", ""), x_, y_):
                    alan_mola[1] = 0
                    return
            except Exception as e_a:
                print("alan:", e_a)
                pydirectinput.press("esc")
            alan_mola[1] += 1
            if alan_mola[1] >= 3:                     # alana gidilemiyor: bos durmasin, bir sure serbest kassin
                alan_mola[0], alan_mola[1] = time.time() + ayar.get("alan_mola_dk", 20) * 60, 0
                print(f"{time.strftime('%H:%M:%S')}  alan: 3 kez alana gidilemedi - {ayar.get('alan_mola_dk', 20)} dk alan modu askida, serbest kasiliyor")
            return
        try:
            if gezin_buyuk():
                return
        except Exception as e_g:
            print("gezin_buyuk:", e_g)
            pydirectinput.press("esc")
        """Etrafta uygun hedef yok: haritadan rastgele bir cayir noktasi secip oraya yurur
        (koy merkezi ve su haric); yolda slot gorurse durur."""
        kapat_d = harita_ac()
        k = kare_al(h)
        yuk_, gen_ = k.shape[:2]
        if kapat_d is None:
            aci = random.uniform(0, 2 * math.pi)
            tikla(gen_ // 2 + 600 * math.cos(aci), yuk_ * 0.55 + 330 * math.sin(aci))
        else:
            cx, cy = kapat_d
            x0, y0, x1, y1 = cx - 242, cy + 17, cx + 12, cy + 334
            p = k[y0:y1, x0:x1].astype(int)
            npc = ((p[..., 1] > 180) & (p[..., 0] < 140) & (p[..., 2] < 140)).astype(np.uint8)
            koy = cv2.dilate(npc, np.ones((61, 61), np.uint8)) > 0
            cayir = (p[..., 1] > p[..., 0] + 5) & (p[..., 1] > p[..., 2] + 10) & (p[..., 1] > 55) & (p[..., 1] < 170)
            cayir = cv2.erode(cayir.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
            aday = np.argwhere(cayir & ~koy)
            if len(aday) and ayar.get("engel_hafiza", True):
                try:
                    pts_ = engel_noktalari(kayitli_harita_bul(p.astype(np.uint8)) or "")
                    keep_ = np.ones(len(aday), bool)
                    for ex_, ey_, say_ in pts_:
                        keep_ &= np.hypot(aday[:, 1] / 254 - ex_, aday[:, 0] / 317 - ey_) >= (0.03 if say_ >= 2 else 0.02)
                    if keep_.any():
                        aday = aday[keep_]
                except Exception as e_ef:
                    print("engel hafiza filtre:", e_ef)
            if len(aday):
                yy, xx = bolge_sec(kapat_d, aday)
                print(f"{time.strftime('%H:%M:%S')}  hedef yok - haritadan baska bolgeye yuruyor")

                def _slot_var(kf_):
                    tum_ = kirmizi_etiketler(kf_)
                    return sum(1 for t in tum_ for u in tum_
                               if math.hypot(t[0] - u[0], t[1] - u[1]) < ayar["slot_yaricapi_piksel"]) >= 9

                yoldan = harita_yuru(kapat_d, x0 + xx, y0 + yy, ayar["gezinme_en_uzun_sn"] * 2, _slot_var)
                if yoldan is None:
                    tikla(x0 + xx, y0 + yy)
                else:
                    tikla(*kapat_d)
                    pydirectinput.moveTo(ox_son[0] + gen_ // 2, ox_son[1] + int(yuk_ * 0.8))
                    return
            time.sleep(0.4)
            tikla(*kapat_d)
        pydirectinput.moveTo(ox_son[0] + gen_ // 2, ox_son[1] + int(yuk_ * 0.8))
        bas, onceki, durgun = time.time(), None, 0
        while time.time() - bas < ayar["gezinme_en_uzun_sn"] and durum["calis"] and not durum["duraklat"]:
            time.sleep(0.8)
            kf = kare_al(h)
            if olum_denetle(kf):
                return
            if can_orani(kf) < ayar["can_esigi"]:
                pydirectinput.press(ayar["can_potu_tusu"])
            if can_orani(kf) < ayar["yolda_saldiri_can"]:
                return                                           # saldiri var: kesmeye don
            tum = kirmizi_etiketler(kf)
            if sum(1 for t in tum for u in tum if math.hypot(t[0] - u[0], t[1] - u[1]) < ayar["slot_yaricapi_piksel"]) >= 9 \
                    or beyaz_etiketler(kf):
                tikla(gen_ // 2, int(yuk_ * 0.58))               # dur: slot ya da metin goruldu
                return
            mh, _ = mini_harita(kf)
            if onceki is not None:
                durgun = durgun + 1 if float(np.abs(mh - onceki).mean()) < 0.6 else 0
                if durgun >= 4:
                    return                                       # vardi ya da takildi
            onceki = mh

    def egitmene_git():
        return npc_git(ayar["egitmen_anahtar"], [ayar["beceri_grubu"]], "egitmen")

    def gorev_listesi():
        su_an[0] = "gorev_listesi"
        """Gorev penceresini (N) acip yazisini okur (goruntusunu de kaydeder)."""
        pencereleri_kapat()
        pydirectinput.press(ayar["gorev_tusu"])
        time.sleep(1.0)
        pydirectinput.moveTo(ox_son[0] + 960, ox_son[1] + 1000)
        time.sleep(0.3)
        kf = kare_al(h)
        Image.fromarray(kf).save(os.path.join(KLASOR, "goruntu", "gorev_listesi.png"))
        pencere = sorted(acik_pencereler(kf, kapat_s))
        if pencere:
            cx, cy = pencere[0]
            kutu = (max(0, cx - 520), cy + 10, cx + 15, cy + 560)
        else:
            kutu = (0, 60, kf.shape[1], kf.shape[0] - 120)
        satirlar = oku.oku(kf, kutu=kutu, olcek=3)
        yazi = " | ".join(t["yazi"] for t in satirlar)
        if pencere:
            for t in satirlar:
                if oku.benzer(t["yazi"], "tamamlandi"):
                    taban = orta_parlaklik(kf)
                    tikla(pencere[0][0] - 252, t["y"] + 8)       # gorevin parsomen simgesi
                    time.sleep(1.3)
                    if diyalog_acik(kare_al(h), taban):
                        diyalog_ilerlet([], "gorev", taban)
                        print(f"{time.strftime('%H:%M:%S')}  tamamlanan gorevin odulu alindi")
                    break
        pencereleri_kapat()
        return yazi

    son_gorev_metni = [zaman_oku("gorev_metni")]

    def gorev_metni_topla():
        su_an[0] = "gorev_metni_topla"
        """Gorev penceresindeki her gorevin parsomen simgesine tiklar, aciklama metnini OKUR (secim/onay yapmaz;
        yalniz 'Devam' ile sonraki sayfaya gecer, en cok 5 sayfa), gorev_metinleri.json'a yazar. Ayni gorev gunde 1 kez."""
        bugun = time.strftime("%Y-%m-%d")
        dk = os.path.join(KLASOR, "goruntu", "gorev_metin")
        os.makedirs(dk, exist_ok=True)

        def pencere_ac():
            pencereleri_kapat()
            pydirectinput.press(ayar["gorev_tusu"])
            time.sleep(1.0)
            pydirectinput.moveTo(ox_son[0] + 960, ox_son[1] + 1000)
            time.sleep(0.3)
            kf_ = kare_al(h)
            pen_ = sorted(acik_pencereler(kf_, kapat_s))
            return kf_, pen_

        def zaman_satiri(u):
            sd_ = oku.sade(u["yazi"])
            return "zaman" in sd_.split() or sd_.startswith("kalan") or oku.benzer(u["yazi"], "tamamlandi")

        kf, pencere = pencere_ac()
        if not pencere:
            pencereleri_kapat()
            return 0
        cx, cy = pencere[0]
        satirlar = oku.oku(kf, kutu=(max(0, cx - 520), cy + 10, cx + 15, cy + 560), olcek=3)
        satirlar = sorted(satirlar, key=lambda t: t["y"])
        gorevler = []                                   # (ham baslik, simge y)
        for t in satirlar:
            if zaman_satiri(t):
                ust = [u for u in satirlar if 8 < t["y"] - u["y"] < 48 and not zaman_satiri(u) and u["x0"] > cx - 245]
                if ust:
                    gorevler.append((" ".join(u["yazi"] for u in ust), t["y"] + 8))
        veri = gorev_json_oku()
        print(f"{time.strftime('%H:%M:%S')}  gorev metni: {len(gorevler)} baslik: " + " | ".join(g[0] for g in gorevler))
        okunan = 0
        for i, (baslik, sy) in enumerate(gorevler[:8]):
            anahtar = oku.sade(baslik)
            if not anahtar:
                continue
            for k_ in list(veri):                          # OCR gurultusu: benzer eski anahtara esle
                if k_ != "diyaloglar" and k_ != anahtar and oku.benzer(anahtar, k_, 0.85):
                    anahtar = k_
                    break
            kayit = veri.get(anahtar)
            if kayit and kayit.get("son") == bugun:
                continue
            if i > 0:
                kf, pencere = pencere_ac()
                if not pencere:
                    break
                cx, cy = pencere[0]
            taban = orta_parlaklik(kf)
            tikla(cx - 252, sy)
            time.sleep(1.3)
            if not diyalog_acik(kare_al(h), taban):
                print(f"   gorev metni: '{baslik}' icin diyalog acilmadi")
                pencereleri_kapat()
                continue
            sayfalar, goruntuler = [], []
            for sayfa in range(5):
                if win32gui.GetForegroundWindow() != h:
                    break
                kd = kare_al(h)
                if not diyalog_acik(kd, taban):
                    break
                n = len([f_ for f_ in os.listdir(dk) if f_.startswith(bugun)]) + 1
                yol_g = os.path.join(dk, f"{bugun}_{n}.png")
                Image.fromarray(kd).save(yol_g)
                goruntuler.append(os.path.relpath(yol_g, KLASOR))
                yuk_, gen_ = kd.shape[:2]
                sat = oku.oku(kd, kutu=(gen_ // 2 - 215, yuk_ * 0.32, gen_ // 2 + 215, yuk_ * 0.68), olcek=4)
                metin = " ".join(t["yazi"].strip() for t in sat if t["yazi"].strip())
                tum_s = oku.sade(metin)
                if any(w in tum_s for w in ("satin al", "nesne market", "fiyat", "magaza", "satici")):
                    break
                if sayfalar and metin == sayfalar[-1]:
                    break
                sayfalar.append(metin)
                kisa = [t for t in sat if len(oku.sade(t["yazi"])) <= 34]
                kelimeler = set(w for t in kisa for w in oku.sade(t["yazi"]).split())
                secim = kelimeler & {"evet", "hayir", "kabul", "ret", "vazgec", "reddet", "onayla"}
                devam = [t for t in kisa if any(w in oku.sade(t["yazi"]).split() for w in ("devam", "ileri", "sonraki"))]
                if secim or not devam:
                    break                               # secim ya da belirsiz/Tamam-Kapat: hicbir seye basma, Esc ile cik
                tikla(devam[0]["x"], devam[0]["y"])
                time.sleep(0.8)
                pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
            for _ in range(3):
                pydirectinput.press("esc")
                time.sleep(0.25)
            if sayfalar:
                veri = gorev_json_oku()                 # diyalog_kaydet de dosyaya yazmis olabilir
                eski = veri.get(anahtar, {})
                veri[anahtar] = {"baslik": baslik, "metin": sayfalar, "ilk": eski.get("ilk", bugun), "son": bugun,
                                 "goruntu": goruntuler}
                gorev_json_yaz(veri)
                okunan += 1
                print(f"{time.strftime('%H:%M:%S')}  gorev metni kaydedildi: {baslik} ({len(sayfalar)} sayfa)")
        pencereleri_kapat()
        return okunan

    gy = {"k": None, "adim": 0, "ilerleme": 0.0, "adim_bas": 0.0, "kalan": None, "ceza": {}, "bos": 0.0,
          "kasil_son": 0.0, "deneme": 0}

    def gorev_yurut(yazi):
        """gorev_tablosu.json'a gore gorevleri sirayla yurutur. NPC'ye yurudu/konustuysa True."""
        su_an[0] = "gorev_yurut"
        simdi = time.time()
        tablo = gy_mod.tablo_yukle()
        if not tablo:
            return False
        yalniz = bool(ayar.get("yalniz_gorev"))
        gor, kalan_map, metinler = [], {}, None
        for b_, kal_ in gy_mod.basliklari_ayir(yazi):
            k_ = gy_mod.esle(b_, tablo)
            if k_ is None:
                metinler = metinler if metinler is not None else gorev_json_oku()
                ad_ = next((kk for kk in metinler if kk != "diyaloglar" and difflib.SequenceMatcher(None, kk, b_).ratio() >= 0.8), None)
                if gy_mod.eksik_yaz(b_, (metinler.get(ad_) or {}).get("metin") if ad_ else None):
                    print(f"{time.strftime('%H:%M:%S')}  gorev: tabloda yok -> gorev_tablosu_eksik.json: {b_}")
                continue
            if k_ not in kalan_map:
                gor.append(k_)
                kalan_map[k_] = kal_
        cur = gy["k"]
        if cur:
            if cur not in kalan_map:
                print(f"{time.strftime('%H:%M:%S')}  gorev: '{cur}' listeden kalkti (bitti)")
                cur = gy["k"] = None
            else:
                if kalan_map[cur] is not None and gy["kalan"] is not None and kalan_map[cur] < gy["kalan"]:
                    gy["ilerleme"] = simdi
                gy["kalan"] = kalan_map[cur]
                if simdi - gy["ilerleme"] > 1200:
                    print(f"{time.strftime('%H:%M:%S')}  gorev takildi: {cur} - sona alindi")
                    gy["ceza"][cur] = simdi + 1800
                    cur = gy["k"] = None
        if not cur:
            aday = sorted((tablo[k_].get("sira", 99), k_) for k_ in gor
                          if not tablo[k_].get("atla") and gy["ceza"].get(k_, 0) < simdi
                          and (tablo[k_].get("adimlar") or k_ == "av gorevi"))
            if aday and simdi - gy["kasil_son"] > 600:
                cur = gy["k"] = aday[0][1]
                gy.update(adim=0, ilerleme=simdi, adim_bas=simdi, kalan=kalan_map[cur], bos=0.0, deneme=0)
            elif aday:
                return False                                   # kasilma beklemesi (10 dk)
            else:
                if not gy["bos"]:
                    gy["bos"] = simdi
                if not yalniz or simdi - gy["bos"] > 300:
                    ayar["sadece_hedefler"] = []
                    if simdi - gy["kasil_son"] > 600:
                        gy["kasil_son"] = simdi
                        print(f"{time.strftime('%H:%M:%S')}  gorev: yapilacak adim yok - kasiliyor")
                else:
                    ayar["sadece_hedefler"] = ["(gorev yaratigi yok)"]
                return False
        kayit = tablo[cur]
        adimlar = kayit.get("adimlar") or [{"tur": "kes", "yaratik": "<gorev listesinden>"}]
        if gy["adim"] >= len(adimlar):
            gy["ceza"][cur] = simdi + (600 if kayit.get("tekrar") else 1800)
            print(f"{time.strftime('%H:%M:%S')}  gorev: '{cur}' adimlari bitti ({'tekrar: sona' if kayit.get('tekrar') else 'listede kaldi: bekle'})")
            gy["k"] = None
            return False
        a_ = adimlar[gy["adim"]]
        tur = a_.get("tur")
        hedef = a_.get("yaratik") or a_.get("npc") or ""
        if str(hedef).startswith("<"):
            hedef = av_aranan[0] if av_aranan else ""
        etiket = (cur, gy["adim"])
        if gy.get("son_etiket") != etiket:
            gy["son_etiket"] = etiket
            print(f"{time.strftime('%H:%M:%S')}  gorev sirasi: {cur} (adim {gy['adim'] + 1}/{len(adimlar)}: {tur} {hedef or '?'})")
        if tur in ("kes", "esya_dusur"):
            ayar["sadece_hedefler"] = [hedef] if hedef else (["(gorev yaratigi yok)"] if yalniz else [])
            if tur == "esya_dusur" and hedef:
                if hedef not in aranan_durum:
                    aranan_durum.append(hedef)
                    del aranan_durum[:-5]
                    durum_yaz(aranan=aranan_durum)
                if simdi - gy["adim_bas"] >= ayar.get("gorev_esya_dk", 5) * 60:      # esya dususu izi yok: sureye gore teslime
                    gy["adim"] += 1
                    gy["adim_bas"] = gy["ilerleme"] = simdi
            return False
        if tur in ("npc_ver", "npc_konus"):
            if not hedef or win32gui.GetForegroundWindow() != h or not sakin_mi(kare_al(h)):
                return False
            ok_ = npc_git(hedef, [], "npc_gorev")
            print(f"{time.strftime('%H:%M:%S')}  gorev npc '{hedef}' ({tur}): {'konusuldu' if ok_ else 'olmadi'}")
            if ok_:
                gy["adim"] += 1
                gy["adim_bas"] = gy["ilerleme"] = simdi
                gy["deneme"] = 0
            else:
                gy["deneme"] += 1
                if gy["deneme"] >= 3:
                    print(f"{time.strftime('%H:%M:%S')}  gorev takildi: {cur} - sona alindi")
                    gy["ceza"][cur] = simdi + 1800
                    gy["k"] = None
            return True
        gy["adim"] += 1                                         # bilinmeyen tur: atla
        return False

    def npc_gorevi_yap():
        su_an[0] = "npc_gorevi_yap"
        """Once tamamlanan gorev odullerini alir, sonra haritada halkali (gorev veren) NPC'lere,
        sonra gorev listesinde adi gecen NPC'lere gidip konusur."""
        if win32gui.GetForegroundWindow() != h:
            return False
        yazi = gorev_listesi()
        print(f"{time.strftime('%H:%M:%S')}  gorevler: {yazi}")
        if ayar.get("gorev_metni_topla") and time.time() - son_gorev_metni[0] > 1800 and sakin_mi(kare_al(h)):
            son_gorev_metni[0] = time.time()
            zaman_yaz("gorev_metni", son_gorev_metni[0])
            try:
                gorev_metni_topla()
            except Exception:
                import traceback
                print("gorev_metni_topla hatasi:", traceback.format_exc()[-400:])
                pencereleri_kapat()
        m_av = re.search(r"av gorevi ((?:[a-z]+ ){1,4}?)(?:zaman|kalan)", " ".join(oku.sade(yazi).split()) + " ")
        yeni_av = [m_av.group(1).strip()] if m_av and len(m_av.group(1).replace(" ", "")) >= 5 else []
        if yeni_av != av_aranan:
            av_aranan[:] = yeni_av
        yurutucu = ayar.get("gorev_yurutucu", True) and ayar.get("profil") in ("yalniz_gorev", "gorev")
        if yurutucu and gorev_yurut(yazi):
            return True
        if ayar.get("yalniz_gorev") and not yurutucu:      # yalniz gorev: yalniz gorevin istedigi yaratik kesilir
            ayar["sadece_hedefler"] = list(av_aranan) or ["(gorev yaratigi yok)"]
            print(f"{time.strftime('%H:%M:%S')}  av gorevi hedefi: {yeni_av[0] if yeni_av else 'yok'}")
        if not ayar["npc_gorevleri"]:               # yalniz av gorevi icin liste okundu; NPC'ye gidilmez
            return False
        if ayar["halkali_npc"] and halkali_npc_git():
            return True
        if yurutucu:
            return False
        denemeler = durum_oku().get("npc_deneme", {})
        for kelime, npc in ayar["gorev_npcleri"].items():
            if not oku.benzer(yazi, kelime):
                continue
            son = denemeler.get(npc, 0)
            if time.time() - son < ayar["npc_tekrar_dk"] * 60:
                continue
            denemeler[npc] = time.time()
            durum_yaz(npc_deneme=denemeler)
            sonuc = npc_git(npc, [], "npc_gorev")
            print(f"{time.strftime('%H:%M:%S')}  npc gorevi '{npc}': {'konusuldu' if sonuc else 'olmadi'}")
            return True
        return False

    def yetenek_penceresi_ac():
        su_an[0] = "yetenek_penceresi_ac"
        """Karakter penceresini acip Yetenekler sekmesine gecer; pencerenin resmini goruntu\beceri_kirp.png'ye
        kaydeder (panel bu resimde beceri sirasini sectirir). Donus: kapat dugmesi (cx, cy) ya da None."""
        pencereleri_kapat()
        once = acik_pencereler(kare_al(h), kapat_s)
        pydirectinput.press(ayar["karakter_tusu"])
        time.sleep(0.9)
        sonra = acik_pencereler(kare_al(h), kapat_s)
        yeni = [q for q in sonra if all(abs(q[0] - o[0]) > 6 or abs(q[1] - o[1]) > 6 for o in once)]
        if not yeni:                       # kapanmayan baska pencere (indirim vb.) yuzunden yanlisini secme
            return None
        cx, cy = yeni[0]
        tikla(cx - 176, cy + 412)                               # Yetenekler sekmesi
        time.sleep(0.9)
        pydirectinput.moveTo(ox_son[0] + cx + 300, ox_son[1] + cy + 500)
        time.sleep(0.3)
        kf = kare_al(h)
        kx0, ky0 = max(0, cx - 320), max(0, cy - 10)
        Image.fromarray(kf[ky0:cy + 440, kx0:cx + 20]).save(os.path.join(KLASOR, "goruntu", "beceri_kirp.png"))
        durum_yaz(beceri_kirp_koken=[kx0 - cx, ky0 - cy])
        return cx, cy

    def beceri_puani_ver():
        su_an[0] = "beceri_puani_ver"
        """Karakter penceresinin Yetenekler sekmesinde bos beceri puanlarini dagitir:
        ilk seferde her beceriye birer puan, sonra hepsi oncelikli beceriye (hava kilici: 2. satir sag)."""
        yol_b = os.path.join(KLASOR, "sablon", "beceri_arti.png")
        if not os.path.exists(yol_b):
            return
        b_arti = cv2.imread(yol_b, cv2.IMREAD_GRAYSCALE)
        acik_ = yetenek_penceresi_ac()
        if acik_ is None:
            print("beceri: karakter penceresi acilamadi")
            return
        cx, cy = acik_

        def artilar():
            kf = kare_al(h)
            g = cv2.cvtColor(kf, cv2.COLOR_RGB2GRAY)[cy + 40:cy + 260, max(0, cx - 300):cx + 10]
            r = cv2.matchTemplate(g, b_arti, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(r >= 0.85)
            liste = []
            for x, y in zip(xs, ys):
                p = (int(x) + max(0, cx - 300) + 7, int(y) + cy + 40 + 7)
                if all(abs(p[0] - q[0]) > 6 or abs(p[1] - q[1]) > 6 for q in liste):
                    liste.append(p)
            return sorted(liste, key=lambda p: (p[1], p[0]))

        liste = artilar()
        Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", "beceri_penceresi.png"))
        verilen = 0
        if liste and ayar["beceri_birer_ver"] and not durum_oku().get("beceri_birer_verildi"):
            for px, py in liste:
                tikla(px, py)
                verilen += 1
                time.sleep(0.5)
            durum_yaz(beceri_birer_verildi=True)
            pydirectinput.moveTo(ox_son[0] + cx + 300, ox_son[1] + cy + 500)
            time.sleep(0.4)
            liste = artilar()
        # sirayla: bir becerinin arti dugmesi kalmadiysa (master oldu ya da kapali) siradakine gecilir;
        # hic arti kalmadiysa puan bitmistir. Listede olmayan beceriye puan verilmez.
        dokunulan = []
        sira_ = ayar["beceri_sira_konum"] or [[BECERI_KONUM[a][0] + 11, BECERI_KONUM[a][1] - 13]
                                              for a in ayar["beceri_sirasi"] if a in BECERI_KONUM]
        for i_, (dx_, dy_) in enumerate(sira_):
            if not liste:
                break
            ix_, iy_ = cx + dx_, cy + dy_                  # beceri ikonunun merkezi; arti sol altinda
            n_ = 0
            for _ in range(25):
                hedef = sorted([p for p in liste if abs(p[0] - ix_) < 28 and abs(p[1] - iy_) < 28],
                               key=lambda p: abs(p[0] - ix_) + abs(p[1] - iy_))
                if not hedef:
                    break
                tikla(*hedef[0])
                verilen += 1
                n_ += 1
                time.sleep(0.5)
                pydirectinput.moveTo(ox_son[0] + cx + 300, ox_son[1] + cy + 500)
                time.sleep(0.3)
                liste = artilar()
            if n_:
                dokunulan.append(f"{i_ + 1}. beceri +{n_}")
            if liste:
                continue                                # bu becerinin artisi bitti ama puan var: siradaki
            break
        if dokunulan:
            print(f"{time.strftime('%H:%M:%S')}  beceri sirasi: {', '.join(dokunulan)}")
        print(f"{time.strftime('%H:%M:%S')}  beceri: {verilen} puan verildi (kalan arti: {len(liste)})")
        pencereleri_kapat()

    egitim_gerek = bool(ayar["beceri_grubu"]) and kapat_s is not None and not durum_oku().get("egitmen_denendi")
    olum_deneme = 0
    beceri_gerek = False          # acilista degil, "beceri gelistir" simgesi gorununce
    yeniden_baslat = [False]
    sev_aday = [None, 0]
    son_c_seviye = [zaman_oku("c_seviye") if benim_sev else 0.0]   # yeniden acilista seviye biliniyorsa C penceresini hemen acma
    exp_olcum = []                # (zaman, seviye, exp, gerekli)
    exp_toplam = [0, time.time(), None]   # toplam kazanc, olcum baslangici, saatlik

    def exp_kaydet(sev_, exp_, gerekli_):
        """Okunan (seviye, exp, gerekli) kaydedilir; ilk okumadan bu yana saatlik tecrube hesaplanir."""
        simdi_ = time.time()
        if exp_olcum:
            t0, s0, e0, g0 = exp_olcum[-1]
            if sev_ == s0:
                kazanc_ = exp_ - e0
            elif sev_ == s0 + 1:
                kazanc_ = (g0 - e0) + exp_                      # seviye atladi
            else:
                kazanc_ = None                                   # okuma hatasi / cok seviye: yeni baslangic
                exp_olcum.clear()
                exp_toplam[0], exp_toplam[1] = 0, simdi_
            if kazanc_ is not None and kazanc_ >= 0:
                exp_toplam[0] += kazanc_
        else:
            exp_toplam[0], exp_toplam[1] = 0, simdi_
        exp_olcum.append((simdi_, sev_, exp_, gerekli_))
        gecen_ = simdi_ - exp_toplam[1]
        if gecen_ > 120:
            saat_ = exp_toplam[0] / gecen_ * 3600
            exp_toplam[2] = round(saat_)
            kalan_ = (gerekli_ - exp_) / saat_ * 60 if saat_ > 0 else None
            print(f"{time.strftime('%H:%M:%S')}  tecrube: saatte {saat_:,.0f} exp ({gecen_ / 60:.0f} dk olcum)"
                  + (f", seviye atlamaya ~{kalan_:.0f} dk" if kalan_ else ""))
            with open(os.path.join(KLASOR, "exp_olcum.csv"), "a", encoding="utf-8") as f_:
                f_.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{sev_},{exp_},{gerekli_},{round(saat_)}\n")

    def seviye_karakterden():
        """C ile karakter penceresini acip portrenin altindaki 'Seviye' kutusunu okur, pencereyi kapatir."""
        su_an[0] = "seviye (C penceresi)"
        pencereleri_kapat()
        pydirectinput.press(ayar["karakter_tusu"])
        time.sleep(0.9)
        k_ = kare_al(h)
        pencere = sorted(acik_pencereler(k_, kapat_s))
        sev_ = None
        if pencere:
            cx, cy = pencere[0]
            for t in oku.oku(k_, kutu=(cx - 290, cy + 55, cx - 220, cy + 105), olcek=3):
                rak = "".join(c for c in t["yazi"] if c.isdigit())
                if rak and 1 <= int(rak) <= 120:
                    sev_ = int(rak)
            sayilar_ = []
            for kutu_ in ((cx - 215, cy + 75, cx - 110, cy + 103), (cx - 108, cy + 75, cx + 12, cy + 103)):
                rak_ = "".join(c for t in oku.oku(k_, kutu=kutu_, olcek=3) for c in t["yazi"] if c.isdigit())
                sayilar_.append(int(rak_) if rak_ else None)
            if sev_ and None not in sayilar_:
                exp_kaydet(sev_, sayilar_[0], sayilar_[1])
            tikla(cx, cy)                                       # pencereyi kapat
            time.sleep(0.2)
        if sev_ is None:
            Image.fromarray(k_).save(os.path.join(KLASOR, "goruntu", "seviye_okunamadi.png"))
            print(f"{time.strftime('%H:%M:%S')}  seviye: karakter penceresinden okunamadi")
            son_c_seviye[0] = time.time() - ayar["seviye_kontrol_dk"] * 60 + 120   # 2 dk sonra yeniden dene
        su_an[0] = "ana dongu (hedef ariyor)"
        return sev_

    son_beceri_simge = 0.0
    son_metin_tarama = 0.0
    metin_gorulen = []
    son_neden = [""]
    son_npc_gorev = zaman_oku("npc_gorev", time.time() - 9999)   # yeniden acilista gorev okumasi bastan yapilmasin
    son_sayfa = 0.0
    son_kamera_uzak = 0.0
    son_kamera_egim = [0.0]

    def kamera_egim_ayarla():
        son_kamera_egim[0] = time.time()
        birak()
        pydirectinput.keyDown("g")
        time.sleep(1.2)                                         # en tepe: her seferinde ayni baslangic
        pydirectinput.keyUp("g")
        time.sleep(0.05)
        pydirectinput.keyDown("t")
        time.sleep(ayar["kamera_egim_t_sn"])                    # oradan yataya dogru
        pydirectinput.keyUp("t")
        time.sleep(0.2)
        Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", "kamera_ayar.png"))
    son_yolo_veri = [0.0]
    son_gezin = [0.0]
    engel_kac = [False]
    son_hamle = [0.0]
    son_savas = [0.0]
    hemen_savas = [0.0]   # yolda slot gorulup dalindi: bu andan 10 sn yan isler (envanter, gorev, guclendirme) yok
    atla = []                     # ulasilamayan hedefler (zaman, x, y): kisa sure secilmez
    alan_don = [False]
    dusuk_gezin, dusuk_izin = [], [0.0]
    son_diyalog_bakis = 0.0
    yol_sf = os.path.join(KLASOR, "sablon", "sayfa1.png")
    sayfa_s = cv2.imread(yol_sf, cv2.IMREAD_GRAYSCALE) if os.path.exists(yol_sf) else None
    ulasilamayan = 0
    guc = {"hedef": None, "son": 0.0, "eksik": 0}

    guc_tus_son = {t_["tus"]: zaman_oku("guc_" + t_["tus"]) for t_ in ayar["sureli_tuslar"]}   # tus -> son basilma (kalici)
    guc["son"] = max(guc_tus_son.values(), default=0.0)   # yeniden acilista az once yakildiysa hemen tekrar yakma

    def grup_sonu_guclendir():
        """Grup bitince: bekleme suresi dolan guclendirmeyi (hava kilici, ofke) hemen yak - sonraki slota kilicsiz girme."""
        if not ayar["grup_sonu_guc"] or not ayar["sureli_tuslar"]:
            return
        hazir_ = [t for t in ayar["sureli_tuslar"] if time.time() - guc_tus_son.get(t["tus"], 0) >= t["aralik_sn"]]
        if not hazir_ or can_orani(kare_al(h)) < ayar["guc_can_esigi"]:
            return
        birak()
        for t in hazir_:
            pydirectinput.press(t["tus"])
            guc_tus_son[t["tus"]] = time.time()
            zaman_yaz("guc_" + t["tus"], guc_tus_son[t["tus"]])
            time.sleep(0.5)
        guc["son"], guc["eksik"] = time.time(), 0
        print(f"{time.strftime('%H:%M:%S')}  grup sonu: guclendirme yakildi ({', '.join(t['tus'] for t in hazir_)})")

    def guclendir():
        su_an[0] = "guclendir"
        """Guclendirme tuslarina basar ve etki simgesi sayisini ogrenir."""
        k_g = kare_al(h)
        if can_orani(k_g) < ayar["guc_can_esigi"]:          # can yarinin altinda: hava kilici/ofke basma
            return
        once = etki_sayisi(k_g)
        for t in ayar["sureli_tuslar"]:
            pydirectinput.press(t["tus"])
            guc_tus_son[t["tus"]] = time.time()
            zaman_yaz("guc_" + t["tus"], guc_tus_son[t["tus"]])
            time.sleep(0.55)
        time.sleep(0.4)
        sonra = etki_sayisi(kare_al(h))
        guc["son"], guc["eksik"] = time.time(), 0
        guc["hedef"] = sonra if sonra > once or (guc["hedef"] is not None and sonra >= guc["hedef"]) else guc["hedef"]
        if sonra > once:
            print(f"{time.strftime('%H:%M:%S')}  guclendirme yakildi (etki simgesi {once} -> {sonra})")

    def sakin_mi(k):
        """Yakinda yaratik yok ve vurulmuyorum (beklemeli isler ancak o zaman)."""
        if saldiri_altinda():
            return False
        if time.time() - son_savas[0] < 4:
            return False
        yk_, gn_ = k.shape[:2]
        return not any(math.hypot(t[0] - gn_ // 2, t[1] - yk_ * 0.58) < 450 for t in kirmizi_etiketler(k))

    def guc_denetle(k):
        """Etki simgesi azaldiysa (beceri sondu) yeniden yakar; simge ogrenilemediyse sureye gore basar."""
        if not ayar["sureli_tuslar"] or can_orani(k) < ayar["guc_can_esigi"] or not sakin_mi(k):
            return
        gecen = time.time() - guc["son"]
        if guc["hedef"] is None:
            if gecen > min(t["aralik_sn"] for t in ayar["sureli_tuslar"]):
                guclendir()
            return
        n = etki_sayisi(k)
        if n > guc["hedef"]:
            guc["hedef"] = n
        guc["eksik"] = guc["eksik"] + 1 if n < guc["hedef"] else 0
        if guc["eksik"] >= 2 and gecen > ayar["guclendirme_en_az_aralik_sn"]:
            guclendir()

    yol_ol = os.path.join(KLASOR, "sablon", "burada_basla.png")
    olum_s = cv2.imread(yol_ol, cv2.IMREAD_GRAYSCALE) if os.path.exists(yol_ol) else None
    olum_sayac = {"n": 0, "zamanlar": [], "temkin_bitis": 0.0}
    sehirden_cik = [False]
    olum_pencere = {"acik": False, "sehirde": False, "t": 0.0, "yeni": False, "yok": 0}   # sayilan olumun penceresi hala acik mi + verilen karar
    olum_kilit = threading.Lock()                                # ana dongu ve olum bekcisi ayni anda tiklamasin

    def olum_karari():
        """Olumu kaydeder; kisa surede cok olum varsa True (sehirde diril) ve temkin moduna gecer.
        Pencere bu olumden beri hic kapanmadiysa ayni olumdur: yeniden sayilmaz, ilk karar korunur."""
        simdi = time.time()
        if olum_pencere["acik"] and simdi - olum_pencere["t"] < 90:
            olum_pencere["t"], olum_pencere["yeni"], olum_pencere["yok"] = simdi, False, 0
            return olum_pencere["sehirde"]
        olum_sayac["n"] += 1
        olum_sayac["zamanlar"] = [z for z in olum_sayac["zamanlar"] if simdi - z < ayar["olum_dongusu_sn"]] + [simdi]
        kisa_ = [z for z in olum_sayac["zamanlar"] if simdi - z < ayar["dalma_olum_sn"]]
        if len(kisa_) >= ayar["dalma_olum_sayisi"] and simdi > olum_sayac.get("dalma_yok_bitis", 0):
            olum_sayac["dalma_yok_bitis"] = simdi + ayar["dalma_yok_dk"] * 60
            print(f"{time.strftime('%H:%M:%S')}  {len(kisa_)} olum {ayar['dalma_olum_sn']} sn icinde - "
                  f"{ayar['dalma_yok_dk']} dk kalabalik slotlara dalmiyor (yalniz tek/ikili yaratik)")
        if len(olum_sayac["zamanlar"]) >= 2:                   # 2. olumden itibaren: guclu yaratiklardan uzak dur
            olum_sayac["temkin_bitis"] = simdi + ayar["temkin_dk"] * 60
        sehirde_ = len(olum_sayac["zamanlar"]) >= ayar["olum_dongusu_sayisi"]
        if sehirde_:
            olum_sayac["zamanlar"] = []
            if alan_aktif():                                   # cizilen alan bu seviyeye agir: bir sure alana donme
                alan_mola[0] = simdi + 1800
                print(f"{time.strftime('%H:%M:%S')}  alan: olum dongusu - 30 dk cizilen alana donulmuyor")
        olum_pencere.update(acik=True, sehirde=sehirde_, t=simdi, yeni=True, yok=0)
        return sehirde_

    def olum_yok_goruldu():
        """Oyun ondeyken alinan karede olum penceresi yok: 2 ardisik karede yoksa pencere kapanmis say."""
        if olum_pencere["acik"] and not olum_kilit.locked():
            olum_pencere["yok"] = olum_pencere.get("yok", 0) + 1
            if olum_pencere["yok"] >= 2:
                olum_pencere["acik"] = False

    def olum_yaz(k, sehirde, kim=""):
        print(f"{time.strftime('%H:%M:%S')}  oldu ({olum_sayac['n']}. kez){kim} - "
              + ("OLUM DONGUSU: 'Sehirde yeniden basla', temkin modu" if sehirde else "'Burada yeniden basla'")
              + (f" [temkin: en cok Lv {(benim_sev or 0) + ayar['temkin_ust_fark']}]" if temkinde() and not sehirde else ""))
        Image.fromarray(k).save(os.path.join(KLASOR, "goruntu", "olum.png"))

    def olum_penceresi(k):
        """Olum penceresi ekranda mi: (eslesme, sol-ust) ya da None."""
        g = cv2.cvtColor(k[:640, :1100], cv2.COLOR_RGB2GRAY)
        _, en, _, yer = cv2.minMaxLoc(cv2.matchTemplate(g, olum_s, cv2.TM_CCOEFF_NORMED))
        return (en, yer) if en >= 0.8 else None

    def diril_tikla(yer, sehirde, kim):
        """Secilen dugmeye pencere kapanana kadar tiklar (dugmeler oldukten hemen sonra tiklamayi almayabiliyor).
        Kapandiysa True."""
        bas_ = time.time()
        dy_ = olum_s.shape[0] // 2 + (38 if sehirde else 0)
        deneme_ = 0
        while time.time() - bas_ < 25 and durum["calis"]:
            if durum["duraklat"] or win32gui.GetForegroundWindow() != h:
                return False                                    # karar olum_pencere'de duruyor; sonra yeniden denenir
            tikla(yer[0] + olum_s.shape[1] // 2, yer[1] + dy_)
            deneme_ += 1
            time.sleep(1.3)
            if win32gui.GetForegroundWindow() != h:
                return False
            p_ = olum_penceresi(kare_al(h))
            if p_ is None:
                time.sleep(0.3)
                p_ = olum_penceresi(kare_al(h))                 # tek karelik yanlis 'yok'a karsi ikinci bakis
            if p_ is None:
                olum_pencere["acik"] = False
                print(f"{time.strftime('%H:%M:%S')}  {kim}: '{'Sehirde' if sehirde else 'Burada'} yeniden basla' tuttu "
                      f"({deneme_}. tiklama, {time.time() - bas_:.1f} sn)")
                return True
            yer = p_[1]
        print(f"{time.strftime('%H:%M:%S')}  {kim}: dirilme dugmesi 25 sn'de tutmadi ({deneme_} tiklama)")
        return False

    def temkinde():
        return time.time() < olum_sayac["temkin_bitis"]

    def iksir_yenile():
        """Olup dirilince iksir etkileri gider: ikisi de birkac saniye icinde yeniden icilsin."""
        for e_ in envanter:
            if not e_["sandik"]:
                e_["sonraki"], e_["ayni"], e_["bekle"] = time.time() + 4, False, 22
        print(f"{time.strftime('%H:%M:%S')}  dirildi - iksirler yeniden icilecek")

    def dirilince_uzaklas():
        """Dirildigim yerde cok yaratik varsa kalabaligin tersine, bos yone kos ve pot bas."""
        k_ = kare_al(h)
        yk_, gn_ = k_.shape[:2]
        kx_, ky_ = gn_ // 2, yk_ * 0.58
        yakin_ = [t for t in kirmizi_etiketler(k_) if math.hypot(t[0] - kx_, t[1] + 45 - ky_) < 380]
        if len(yakin_) < ayar["dirilince_kalabalik"]:
            return
        ort_x = sum(t[0] for t in yakin_) / len(yakin_)
        ort_y = sum(t[1] + 45 for t in yakin_) / len(yakin_)
        aci_ = math.atan2(ky_ - ort_y, kx_ - ort_x)           # kalabaligin tersi
        print(f"{time.strftime('%H:%M:%S')}  dirildim ama yanimda {len(yakin_)} yaratik var - uzaklasiyor")
        for _ in range(3 if len(yakin_) >= 6 else 2):
            tikla(*bos_yon(kare_al(h), aci_, 430, 280))
            for _ in range(6):
                time.sleep(0.25)
                pydirectinput.press(ayar["can_potu_tusu"])
        pydirectinput.moveTo(ox_son[0] + gn_ // 2, ox_son[1] + int(yk_ * 0.75))

    def olum_denetle(k):
        """Olum penceresi aciksa 'Burada yeniden basla'ya tiklar. Tikladiysa True."""
        if olum_s is None or not ayar["olunce_yeniden_basla"]:
            return False
        p_ = olum_penceresi(k)
        if p_ is None:
            if win32gui.GetForegroundWindow() == h:
                olum_yok_goruldu()
            return False
        if not olum_kilit.acquire(blocking=False):             # olum bekcisi zaten ilgileniyor
            time.sleep(1.0)
            return True
        try:
            k = kare_al(h)                                      # kilit beklerken bekci kapatmis olabilir: taze bak
            p_ = olum_penceresi(k)
            if p_ is None:
                return False
            birak()
            sehirde = olum_karari()
            if olum_pencere["yeni"]:
                olum_yaz(k, sehirde)
            time.sleep(0.6)
            if not diril_tikla(p_[1], sehirde, "olum"):
                return True                                     # tutmadi: sonraki turda yeniden denenir (karar korunur)
            if sehirde:
                time.sleep(3.0)
                sehirden_cik[0] = True                          # ana dongu: koyden disari, uygun bolgeye yuru
            time.sleep(1.5)
            pydirectinput.moveTo(ox_son[0] + k.shape[1] // 2, ox_son[1] + int(k.shape[0] * 0.75))
            guc["son"], guc["hedef"] = 0.0, None               # dirilince: can %50'yi gecince guc_denetle yeniden yakar
            iksir_yenile()
            if not sehirde:
                dirilince_uzaklas()
            return True
        finally:
            olum_kilit.release()

    giris = {"son": 0.0, "bekleme_bas": 0.0, "kopuk": False}

    def hizli_cubuk_puani(k):
        yk, gn = k.shape[:2]
        if sayfa_s is None:
            return 1.0
        b = cv2.cvtColor(k[yk - 40:yk - 8, gn // 2 + 220:gn // 2 + 260], cv2.COLOR_RGB2GRAY)
        if b.std() < 8:                                         # duz renk: arayuz yok
            return 0.0
        return float(cv2.minMaxLoc(cv2.matchTemplate(b, sayfa_s, cv2.TM_CCOEFF_NORMED))[1])

    def giris_denetle(k):
        """Oyun arayuzu (hizli cubuk) yoksa ekrani okur: giris ekrani, karakter secimi ya da
        'baglanti koptu' penceresiyse yeniden baglanir. Bir sey yaptiysa True."""
        if time.time() - giris["son"] < 4:
            return time.time() - giris.get("ekranda", 0) < 6        # giris/karakter ekranindaysak ana dongu beklesin
        if hizli_cubuk_puani(k) >= 0.5:
            if giris["kopuk"] and hizli_cubuk_puani(k) >= 0.5:
                giris["kopuk"] = False
                giris.pop("bilinmeyen_bas", None)
                print(f"{time.strftime('%H:%M:%S')}  oyuna yeniden girildi")
                guc["son"], guc["hedef"] = 0.0, None             # guclendirmeleri bastan yak
                time.sleep(2.0)
            return False
        giris["son"] = time.time()
        yk, gn = k.shape[:2]
        satirlar = (oku.oku(k, kutu=(0, yk * 0.2, gn // 2, yk * 0.95), olcek=2)        # sol (karakter paneli)
                    + oku.oku(k, kutu=(gn // 2, yk * 0.2, gn, yk * 0.95), olcek=2))     # sag
        yazi = oku.sade(" ".join(t["yazi"] for t in satirlar))

        def var(*kelimeler):
            return sum(1 for w in kelimeler if oku.benzer(yazi, w))

        def tikla_yazi(*kelimeler):
            for t in satirlar:
                if any(oku.benzer(t["yazi"], w, 0.85) for w in kelimeler):
                    tikla(t["x"], t["y"])
                    return t["yazi"]
            return None

        def kaydet(ad):
            Image.fromarray(k).save(os.path.join(KLASOR, "goruntu", ad))

        an = time.strftime('%H:%M:%S')
        if var("baglanti", "kesildi", "koptu", "disconnect") and var("tamam", "ok", "evet"):
            giris["kopuk"] = True
            kaydet("baglanti_koptu.png")
            print(f"{an}  baglanti koptu penceresi - kapatiliyor")
            if not tikla_yazi("tamam", "ok", "evet"):
                pydirectinput.press("enter")
            time.sleep(3.0)
            return True
        if var("hesap kayit", "hesap olustur", "pin", "baglan") >= 2:
            giris["kopuk"] = True
            birak()
            if var("giris islemi"):
                if not giris["bekleme_bas"]:
                    giris["bekleme_bas"] = time.time()
                if time.time() - giris["bekleme_bas"] > 45:     # takildi: iptal edip yeniden dene
                    print(f"{an}  giris 45 sn surdu - iptal, yeniden deneniyor")
                    tikla_yazi("iptal")
                    giris["bekleme_bas"] = 0.0
                return True
            giris["bekleme_bas"] = 0.0
            giris["ekranda"] = time.time()
            kaydet("giris_ekrani.png")
            print(f"{an}  oyundan atilmis (giris ekrani) - kayitli hesapla baglaniliyor (F1)")
            pydirectinput.press("f1")                           # 'F1 Baglan <kayitli hesap>'
            time.sleep(6.0)
            return True
        if var("basla", "olustur", "sil", "karakter", "cikis", "seviye", "oyun sure", "kralligi") >= 2:
            giris["kopuk"] = True
            giris["ekranda"] = time.time()
            birak()
            kaydet("karakter_secimi.png")
            if var("olustur") and not var("basla"):              # bos yuva secili: yandaki yuvaya gec
                giris["yuva"] = giris.get("yuva", 0) + 1
                ok_x = gn * 0.747 if giris["yuva"] % 4 in (1, 2) else gn * 0.534   # sag ok / sol ok
                tikla(ok_x, yk * 0.861)
                print(f"{an}  karakter secimi: bos yuva - yandaki yuvaya geciliyor ({giris['yuva']})")
                time.sleep(1.2)
                return True
            pydirectinput.press("enter")                        # Vedat: karakter seciminde Enter ile girilir
            time.sleep(3.0)
            ne = None
            if hizli_cubuk_puani(kare_al(h)) < 0.5:              # hala secim ekraninda: 'Basla' dugmesine tikla
                ne = tikla_yazi("oyuna basla", "basla", "baslat", "start")
            print(f"{an}  karakter secim ekrani - Enter" + (f" + '{ne}' tiklandi" if ne else ""))
            time.sleep(6.0)
            return True
        if giris["kopuk"]:                                      # yukleme ekrani vb.: bir sure bekle
            giris.setdefault("bilinmeyen_bas", time.time())
            if time.time() - giris["bilinmeyen_bas"] < 60:
                return True
            kaydet("giris_bilinmeyen.png")
            giris["kopuk"] = False
        giris.pop("bilinmeyen_bas", None)
        return False

    kod_dosyalari = [os.path.join(KLASOR, f) for f in ("bot.py", "oku.py", "rakam.py", "yol.py", "gorev_yurut.py", "sekil.py", "ayar.json")]

    def kod_damgasi():
        return tuple(os.path.getmtime(f) if os.path.exists(f) else 0 for f in kod_dosyalari)

    def kod_saglam():
        """Yeni kod derlenmiyorsa (yarim kalmis duzenleme) yeniden baslatma."""
        import py_compile
        try:
            for f in kod_dosyalari:
                if f.endswith(".py"):
                    py_compile.compile(f, doraise=True)
            with open(kod_dosyalari[-1], encoding="utf-8-sig") as f:
                json.load(f)
            return True
        except Exception:
            return False

    ilk_damga, son_damga_bakis = kod_damgasi(), time.time()

    yol_sh = os.path.join(KLASOR, "sablon", "sohbet_normal.png")
    sohbet_s = cv2.imread(yol_sh, cv2.IMREAD_GRAYSCALE) if os.path.exists(yol_sh) else None

    yol_komut, yol_canli = os.path.join(KLASOR, "komut.json"), os.path.join(KLASOR, "canli.json")
    canli = {"son": 0.0, "baslangic": time.time(), "kilit": threading.Lock()}
    plan = {"sev": None, "p": {"yazi": ""}}
    esya_yazi = ""
    try:                                    # yeniden acilista (kod/ayar degisti) duraklatma korunur
        with open(yol_canli, encoding="utf-8") as f:
            _onceki = json.load(f)
        if _onceki.get("duraklat") and time.time() - _onceki.get("zaman", 0) < 90:
            durum["duraklat"] = True
    except Exception:
        pass

    def arka_test():
        """Deney: pencere arkadayken (1) PrintWindow ile goruntu aliniyor mu, (2) pencereye postalanan tus
        mesaji (envanter tusu) oyunda isliyor mu. Sonuc loga ve goruntu\arka_test_*.png dosyalarina yazilir."""
        import win32con
        import win32ui

        def yakala():
            _, _, w_, h_ = win32gui.GetClientRect(h)
            dc = win32gui.GetWindowDC(h)
            mdc = win32ui.CreateDCFromHandle(dc)
            sdc = mdc.CreateCompatibleDC()
            bm = win32ui.CreateBitmap()
            bm.CreateCompatibleBitmap(mdc, w_, h_)
            sdc.SelectObject(bm)
            ctypes.windll.user32.PrintWindow(h, sdc.GetSafeHdc(), 3)      # yalniz istemci alani + tam icerik
            bilgi = bm.GetInfo()
            dizi = np.frombuffer(bm.GetBitmapBits(True), np.uint8).reshape(bilgi["bmHeight"], bilgi["bmWidth"], 4)
            sonuc = dizi[..., [2, 1, 0]].copy()
            win32gui.DeleteObject(bm.GetHandle())
            sdc.DeleteDC()
            mdc.DeleteDC()
            win32gui.ReleaseDC(h, dc)
            return sonuc

        try:
            onde = win32gui.GetForegroundWindow() == h
            a = yakala()
            Image.fromarray(a).save(os.path.join(KLASOR, "goruntu", "arka_test_1.png"))
            tus = ord(ayar["envanter_tusu"].upper())
            tarama = ctypes.windll.user32.MapVirtualKeyW(tus, 0)
            win32gui.PostMessage(h, win32con.WM_KEYDOWN, tus, (tarama << 16) | 1)
            time.sleep(0.12)
            win32gui.PostMessage(h, win32con.WM_KEYUP, tus, (tarama << 16) | 0xC0000001)
            time.sleep(1.2)
            b = yakala()
            Image.fromarray(b).save(os.path.join(KLASOR, "goruntu", "arka_test_2.png"))
            fark = float(np.abs(a[:, -260:].astype(int) - b[:, -260:].astype(int)).mean()) if a.shape == b.shape else -1
            ekran = kare_al(h)
            uyum = float(np.abs(ekran.astype(int) - b.astype(int)).mean()) if ekran.shape == b.shape else -1
            print(f"{time.strftime('%H:%M:%S')}  arka test: oyun onde={onde} | goruntu {a.shape[1]}x{a.shape[0]} "
                  f"parlaklik {a.mean():.1f} (0 = siyah, alinamiyor) | ekranla fark {uyum:.1f} | "
                  f"tus sonrasi sag serit farki {fark:.1f} (envanter acildiysa buyuk)")
            if fark > 8:                                            # envanter acildi: geri kapat
                win32gui.PostMessage(h, win32con.WM_KEYDOWN, tus, (tarama << 16) | 1)
                time.sleep(0.12)
                win32gui.PostMessage(h, win32con.WM_KEYUP, tus, (tarama << 16) | 0xC0000001)
        except Exception as e_:
            print("arka test hatasi:", repr(e_))

    def bayrak_dene(adimlar=(), sec=False):
        su_an[0] = "bayrak_dene"
        """Envanterdeki koy bayragina sag tiklar, acilan menunun resmini ve yazisini kaydeder, Esc ile kapatir."""
        yol_b = os.path.join(KLASOR, "sablon", "koy_bayragi.png")
        if not os.path.exists(yol_b):
            print("bayrak: sablon yok")
            return
        sab_ = cv2.cvtColor(cv2.imread(yol_b), cv2.COLOR_BGR2RGB)
        pencereleri_kapat()
        pydirectinput.press(ayar["envanter_tusu"])
        time.sleep(0.8)
        k0 = kare_al(h)
        yer_ = esya_bul(k0, sab_)
        if yer_ is None:
            Image.fromarray(k0).save(os.path.join(KLASOR, "goruntu", "bayrak_yok.png"))
            print(f"{time.strftime('%H:%M:%S')}  bayrak: envanterde bulunamadi (goruntu\\bayrak_yok.png)")
            pydirectinput.press(ayar["envanter_tusu"])
            return
        tikla(yer_[0], yer_[1], sag=True)
        time.sleep(1.4)
        pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
        time.sleep(0.3)
        k1 = kare_al(h)
        Image.fromarray(k1).save(os.path.join(KLASOR, "goruntu", "bayrak_menu.png"))
        yuk_, gen_ = k1.shape[:2]
        satirlar = oku.oku(k1, kutu=(gen_ // 2 - 450, yuk_ * 0.12, gen_ // 2 + 450, yuk_ * 0.88), olcek=2)
        print(f"{time.strftime('%H:%M:%S')}  bayrak menusu @{yer_}: " + " | ".join(t["yazi"] for t in satirlar))
        for i_, adim_ in enumerate(adimlar):                  # verilen secenekleri sirayla tikla, sonrakini oku
            sec_ = [t for t in satirlar if oku.benzer(t["yazi"], adim_, 0.8) and len(oku.sade(t["yazi"])) <= 30]
            sira_ = ["shinsoo", "chunjo", "jinno", "close"]          # Empire Warp dugmeleri, 40 px arayla
            if adim_ in ayar["koyler"]:
                sira_ = list(ayar["koyler"])
            if not sec_ and adim_ in sira_:
                bilinen = [(sira_.index(n_), t) for t in satirlar for n_ in sira_
                           if oku.benzer(t["yazi"], n_, 0.8) and len(oku.sade(t["yazi"])) <= 12]
                if bilinen:
                    i0, t0 = bilinen[0]
                    sec_ = [{"x": t0["x"], "y": t0["y"] + (sira_.index(adim_) - i0) * 40, "yazi": adim_}]
                    print(f"   bayrak: '{adim_}' okunamadi, '{sira_[i0]}' dugmesine gore konumdan tiklaniyor")
            if not sec_:
                print(f"   bayrak: '{adim_}' secenegi bulunamadi")
                break
            tikla(sec_[0]["x"], sec_[0]["y"])
            time.sleep(1.4)
            pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
            time.sleep(0.3)
            k1 = kare_al(h)
            Image.fromarray(k1).save(os.path.join(KLASOR, "goruntu", f"bayrak_menu_{i_ + 2}.png"))
            satirlar = oku.oku(k1, kutu=(gen_ // 2 - 450, yuk_ * 0.12, gen_ // 2 + 450, yuk_ * 0.88), olcek=2)
            print(f"   bayrak {i_ + 2}. adim ({adim_} sonrasi): " + " | ".join(t["yazi"] for t in satirlar))
        else:
            if sec:                                        # son secenek tiklandi: isinlaniyor, menu kapanir
                print(f"{time.strftime('%H:%M:%S')}  isinlanma: {' > '.join(adimlar)}")
                time.sleep(6)
                return True
        pydirectinput.press("esc")
        time.sleep(0.4)
        pencereleri_kapat()

    def buyuk_harita_dene():
        pencereleri_kapat()
        pydirectinput.press("m")
        time.sleep(1.2)
        k1 = kare_al(h)
        Image.fromarray(k1).save(os.path.join(KLASOR, "goruntu", "buyuk_harita_m.png"))
        satir = oku.oku(k1, olcek=2)
        print(f"{time.strftime('%H:%M:%S')}  M tusu sonrasi: " + " | ".join(t["yazi"] for t in satir)[:400])
        dugme = [t for t in satir if oku.benzer(t["yazi"], "buyuk harita", 0.8)]
        if dugme:
            tikla(dugme[0]["x"], dugme[0]["y"])
            time.sleep(1.2)
            k2 = kare_al(h)
            Image.fromarray(k2).save(os.path.join(KLASOR, "goruntu", "buyuk_harita_dugme.png"))
            print(f"{time.strftime('%H:%M:%S')}  Buyuk harita dugmesi sonrasi: "
                  + " | ".join(t["yazi"] for t in oku.oku(k2, olcek=2))[:400])
        for _ in range(2):
            pydirectinput.press("esc")
            time.sleep(0.3)
        pencereleri_kapat()

    pot_sab = {}
    for ad_p in ("kirmizi_pot", "mavi_pot"):
        yol_p = os.path.join(KLASOR, "sablon", ad_p + ".png")
        if os.path.exists(yol_p):
            pot_sab[ad_p] = cv2.cvtColor(cv2.imread(yol_p), cv2.COLOR_BGR2RGB)
    pot_yuva = {"kirmizi_pot": -87, "mavi_pot": -49}         # hizli cubukta 1 ve 2 yuvasinin merkezi (ekran ortasina gore)
    pot_doldur_son = [0.0]
    pot_bos_say = {}
    pot_yasak = [0.0]

    def yuva_dolu(k, ad_p):
        yk_, gn_ = k.shape[:2]
        x_ = gn_ // 2 + pot_yuva[ad_p]
        r_ = k[yk_ - 42:yk_ - 10, x_ - 14:x_ + 14].astype(int)
        if ad_p == "kirmizi_pot":
            return int(((r_[..., 0] > 150) & (r_[..., 1] < 90) & (r_[..., 2] < 90)).sum()) >= 6
        return int(((r_[..., 2] > 150) & (r_[..., 0] < 110) & (r_[..., 1] < 110)).sum()) >= 6

    pot_bitti = [0.0]   # can potunun envanterde bulunamadigi son an
    pot_alim = [0.0]    # son pot satin alma denemesi

    def pot_yuvasi_doldur(k):
        """1/2 yuvasi bossa envanterden pot koyar. Bir sey yaptiysa True."""
        if (not ayar["pot_yuvasi_doldur"] or time.time() - pot_doldur_son[0] < 1.5 or not pot_sab
                or time.time() - canli["baslangic"] < 15 or time.time() < pot_yasak[0]):
            return False
        pot_doldur_son[0] = time.time()
        if sayfa_s is None or hizli_cubuk_puani(k) < 0.86:       # hizli cubuk net degil (pencere, yukleme): dokunma
            pot_bos_say.clear()
            return False
        for a_ in pot_sab:
            pot_bos_say[a_] = 0 if yuva_dolu(k, a_) else pot_bos_say.get(a_, 0) + 1
        bos = [a_ for a_ in pot_sab if pot_bos_say.get(a_, 0) >= 3]
        if not bos:
            return False
        for a_ in bos:
            pot_bos_say[a_] = 0
        su_an[0] = "pot yuvasi dolduruluyor"
        birak()
        acildi_ = False
        k_e = k
        if any(esya_bul(k_e, pot_sab[a_]) is None for a_ in bos):
            pydirectinput.press(ayar["envanter_tusu"])
            acildi_ = True
            time.sleep(0.4)
            k_e = kare_al(h)
        yk_, gn_ = k_e.shape[:2]
        for a_ in bos:
            yer_ = esya_bul(k_e, pot_sab[a_])
            if yer_ is None:
                print(f"{time.strftime('%H:%M:%S')}  pot yuvasi: {a_} bos ama envanterde (1. sayfa) {a_} yok")
                if a_ == "kirmizi_pot":                              # can potu bitti: olum dongusune girmesin
                    if time.time() - pot_bitti[0] > 300:
                        print(f"{time.strftime('%H:%M:%S')}  POT BITTI - 30 dk temkinli: kalabaliga dalmiyor, yalniz kolay yaratik (pot alinmali)")
                    pot_bitti[0] = time.time()
                    olum_sayac["temkin_bitis"] = max(olum_sayac["temkin_bitis"], time.time() + 1800)
                    olum_sayac["dalma_yok_bitis"] = max(olum_sayac.get("dalma_yok_bitis", 0), time.time() + 1800)
                continue
            tikla(yer_[0], yer_[1])                                  # potu al (elde)
            time.sleep(0.25)
            tikla(gn_ // 2 + pot_yuva[a_], yk_ - 26)                  # yuvaya birak
            time.sleep(0.35)
            k_e = kare_al(h)
            if yuva_dolu(k_e, a_):
                if a_ == "kirmizi_pot":
                    pot_bitti[0] = 0.0
                print(f"{time.strftime('%H:%M:%S')}  pot yuvasi: {a_} envanterden {1 if a_ == 'kirmizi_pot' else 2} numaraya kondu")
            else:
                tikla(yer_[0], yer_[1])                              # olmadi: eldeki potu yerine geri birak
                time.sleep(0.25)
                print(f"{time.strftime('%H:%M:%S')}  pot yuvasi: {a_} konamadi - geri birakildi; 10 dk denenmeyecek")
                pot_yasak[0] = time.time() + 600
        if acildi_:
            pydirectinput.press(ayar["envanter_tusu"])
            time.sleep(0.2)
        pydirectinput.moveTo(ox_son[0] + gn_ // 2, ox_son[1] + int(yk_ * 0.75))
        return True

    sadece_d = {"son": 0.0, "konum": []}
    etiket_klasor = os.path.join(KLASOR, "sablon", "hedef_etiket")
    os.makedirs(etiket_klasor, exist_ok=True)
    hedef_sablon = {}                                   # hedef adi (sade) -> [kirmizi yazi maskeleri]

    def _slug(ad):
        return "_".join(oku.sade(ad).split())

    for _f in sorted(os.listdir(etiket_klasor)):
        if _f.endswith(".png") and "__" in _f:
            _m = cv2.imread(os.path.join(etiket_klasor, _f), cv2.IMREAD_GRAYSCALE)
            if _m is not None:
                hedef_sablon.setdefault(_f.split("__")[0], []).append(_m)

    def etiket_maskesi(k, t):
        x, y, w, hh = t
        x0 = max(0, x - w // 2)
        p_ = k[max(0, y - hh):y, x0:x0 + w].astype(int)
        return (((p_[..., 0] > 135) & (p_[..., 1] < 60) & (p_[..., 2] < 50)) * 255).astype(np.uint8)

    def sablon_tutar(m, ad):
        for T in hedef_sablon.get(_slug(ad), []):
            if abs(m.shape[1] - T.shape[1]) > 6 or abs(m.shape[0] - T.shape[0]) > 4 or m.sum() == 0:
                continue
            C = cv2.copyMakeBorder(m, 4, 4, 6, 6, cv2.BORDER_CONSTANT, value=0)
            if C.shape[0] < T.shape[0] or C.shape[1] < T.shape[1]:
                continue
            if cv2.minMaxLoc(cv2.matchTemplate(C, T, cv2.TM_CCOEFF_NORMED))[1] < 0.68:
                continue
            w_t = T.shape[1]
            T_s = T[:, int(w_t * 0.55):]                     # adin sonu (ayni onekli adlari ayirir)
            C_s = cv2.copyMakeBorder(m[:, max(0, int(m.shape[1] * 0.55) - 6):], 4, 4, 0, 6, cv2.BORDER_CONSTANT, value=0)
            if (C_s.shape[0] >= T_s.shape[0] and C_s.shape[1] >= T_s.shape[1] and T_s.sum() > 0
                    and cv2.minMaxLoc(cv2.matchTemplate(C_s, T_s, cv2.TM_CCOEFF_NORMED))[1] >= 0.65):
                return True
        return False

    def sablon_ogren(k, t, ad):
        lst = hedef_sablon.setdefault(_slug(ad), [])
        m = etiket_maskesi(k, t)
        if len(lst) >= 6 or m.sum() == 0 or sablon_tutar(m, ad):
            return
        lst.append(m)
        cv2.imwrite(os.path.join(etiket_klasor, f"{_slug(ad)}__{len(lst)}.png"), m)
        print(f"{time.strftime('%H:%M:%S')}  etiket sablonu ogrenildi: {ad} ({len(lst)}. bicim) - artik yazi okumadan taninacak")

    def sadece_suz(k, liste, hemen=False):
        """liste (kirmizi etiketler) icinden yalniz secili canavarlar: once etiket resmi (sablon), olmazsa yazi (OCR)."""
        hedefler_ = ayar["sadece_hedefler"]
        if not hedefler_ or not liste:
            return liste
        hizli = [t for t in liste if any(sablon_tutar(etiket_maskesi(k, t), a_) for a_ in hedefler_)]
        if hizli:
            son_av[0] = time.time()
            sadece_d["konum"] = [(t[0], t[1]) for t in hizli]
            if time.time() - sadece_d["son"] < 3:                  # sablon tuttu: yaziyi seyrek oku (yeni bicim ogrenmek icin)
                return hizli
        if hemen or time.time() - sadece_d["son"] > 1.0:
            sadece_d["son"] = time.time()
            yk_, gn_ = k.shape[:2]
            tum_ = kirmizi_etiketler(k)
            konum = []
            for q in oku.oku(k, kutu=(gn_ // 2 - 650, 60, gn_ // 2 + 650, yk_ - 180), olcek=2, renkli=True):
                ad_t = next((a_ for a_ in hedefler_ if oku.ad_tutar(q["yazi"], a_)), None)
                if ad_t is None or not tum_:
                    continue
                t_ = min(tum_, key=lambda t: abs(t[1] - t[3] / 2 - q["y"]) * 4 + abs(t[0] - q["x"]))
                if abs(t_[1] - t_[3] / 2 - q["y"]) < 14:
                    konum.append((t_[0], t_[1]))
                    sablon_ogren(k, t_, ad_t)
            sadece_d["konum"] = list({*konum, *[(t[0], t[1]) for t in hizli]})
            if konum:
                son_av[0] = time.time()
        return [t for t in liste if any(math.hypot(t[0] - x_, t[1] - y_) < 70 for x_, y_ in sadece_d["konum"])]

    def yuru_test():
        su_an[0] = "yuru_test"
        pencereleri_kapat()
        once = acik_pencereler(kare_al(h), kapat_s)
        pydirectinput.press("m")
        time.sleep(0.8)
        genel = [q for q in acik_pencereler(kare_al(h), kapat_s) if all(abs(q[0] - o[0]) > 6 or abs(q[1] - o[1]) > 6 for o in once)]
        if not genel:
            print("yuru_test: genel harita acilmadi")
            return
        genel = genel[0]
        kg = kare_al(h)
        dugme = [t for t in oku.oku(kg, kutu=(genel[0] - 300, genel[1] + 300, genel[0] + 40, genel[1] + 400), olcek=3)
                 if oku.benzer(t["yazi"], "buyuk harita", 0.75)]
        if not dugme:
            print("yuru_test: Buyuk harita dugmesi yok")
            return
        tikla(dugme[0]["x"], dugme[0]["y"])
        time.sleep(1.0)
        buyuk = [q for q in acik_pencereler(kare_al(h), kapat_s) if abs(q[0] - genel[0]) > 20 and q[0] > 900]
        if not buyuk:
            print("yuru_test: buyuk harita penceresi yok")
            return
        bx, by = buyuk[0]
        kb = kare_al(h)
        x0b, y0b = bx - 899, by + 25
        r_s = cv2.matchTemplate(sari_maske(kb[y0b:by + 549, x0b:bx - 300]), sen_sab, cv2.TM_CCOEFF_NORMED)
        _, v_s, _, l_s = cv2.minMaxLoc(r_s)
        sx, sy = x0b + l_s[0] - 20, y0b + l_s[1] + 8
        Image.fromarray(kb).save(os.path.join(KLASOR, "goruntu", "yuru_test_0.png"))
        print(f"yuru_test: X=({bx},{by}) Sen=({sx},{sy}) eslesme {v_s:.2f}")
        if istek.pop("yuru_test_kapat", False):
            hx, hy = sx + 90, sy
            mh0, _ = mini_harita(kare_al(h))
            tikla(hx, hy)
            time.sleep(0.3)
            tikla(bx, by)                                  # haritayi kapat
            pydirectinput.moveTo(ox_son[0] + 960, ox_son[1] + 1040)
            degisim = []
            for _ in range(6):
                time.sleep(0.5)
                degisim.append(round(float(np.abs(mini_harita(kare_al(h))[0] - mh0).mean()), 2))
            print(f"yuru_test: tikla + harita KAPAT -> mini harita degisimi {degisim}")
            return
        for i_, bicim in enumerate(("tek", "uzun", "cift")):
            hx, hy = sx + 70 + 25 * i_, sy + (20 if i_ % 2 else -20)
            mh0, _ = mini_harita(kare_al(h))
            pydirectinput.moveTo(ox_son[0] + hx, ox_son[1] + hy)
            time.sleep(0.15)
            if bicim == "tek":
                pydirectinput.click()
            elif bicim == "uzun":
                pydirectinput.mouseDown()
                time.sleep(0.15)
                pydirectinput.mouseUp()
            else:
                pydirectinput.click()
                time.sleep(0.08)
                pydirectinput.click()
            pydirectinput.moveTo(ox_son[0] + 960, ox_son[1] + 1040)
            degisim = []
            for _ in range(5):
                time.sleep(0.5)
                mh1, _ = mini_harita(kare_al(h))
                degisim.append(round(float(np.abs(mh1 - mh0).mean()), 2))
            Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", f"yuru_test_{bicim}.png"))
            print(f"yuru_test: {bicim} tik ({hx:.0f},{hy:.0f}) -> mini harita degisimi {degisim}")
        tikla(bx, by)

    harita_klasor = os.path.join(KLASOR, "goruntu", "haritalar")
    os.makedirs(harita_klasor, exist_ok=True)

    def tekerlek(adim, x, y):
        """Fare tekerlegi (adim < 0: uzaklastir) - oyun penceresinde (x, y) uzerinde."""
        import win32api
        import win32con
        pydirectinput.moveTo(ox_son[0] + int(x), ox_son[1] + int(y))
        time.sleep(0.05)
        for _ in range(abs(adim)):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120 if adim > 0 else -120, 0)
            time.sleep(0.04)

    def buyuk_harita_ac_uzak():
        """Buyuk haritayi acip tamamen uzaklastirir. Donus: (bx, by, alan_kutusu, bolge_adi, kare) ya da None."""
        pencereleri_kapat()
        once = acik_pencereler(kare_al(h), kapat_s)
        pydirectinput.press("m")
        genel = None
        for _ in range(10):
            time.sleep(0.12)
            yeni_ = [q for q in acik_pencereler(kare_al(h), kapat_s) if all(abs(q[0] - o[0]) > 6 or abs(q[1] - o[1]) > 6 for o in once)]
            if yeni_:
                genel = yeni_[0]
                break
        if genel is None:
            return None
        kg = kare_al(h)
        dugme = [t for t in oku.oku(kg, kutu=(genel[0] - 300, genel[1] + 300, genel[0] + 40, genel[1] + 400), olcek=3)
                 if oku.benzer(t["yazi"], "buyuk harita", 0.75)]
        if not dugme:
            pydirectinput.press("esc")
            return None
        tikla(dugme[0]["x"], dugme[0]["y"])
        buyuk = None
        for _ in range(12):
            time.sleep(0.12)
            for q in acik_pencereler(kare_al(h), kapat_s):
                if abs(q[0] - genel[0]) > 20 and q[1] < genel[1] + 40 and q[0] > 900:
                    buyuk = q
            if buyuk:
                break
        if buyuk is None:
            pydirectinput.press("esc")
            return None
        bx, by = buyuk
        kutu = (bx - 899, by + 25, bx - 300, by + 549)
        orta_ = ((kutu[0] + kutu[2]) // 2, (kutu[1] + kutu[3]) // 2)

        def dolu(k_):                                         # harita dokusu yuklu mu (siyah degil)
            return float(k_[kutu[1] + 40:kutu[3] - 40, kutu[0] + 20:kutu[2] - 60].mean()) > 25

        for _ in range(8):                                   # adim adim uzaklastir, siyaha donerse geri al
            tekerlek(-1, *orta_)
            time.sleep(0.45)
            if not dolu(kare_al(h)):
                time.sleep(0.6)                             # doku gec yuklenebilir
                if not dolu(kare_al(h)):
                    tekerlek(1, *orta_)
                    time.sleep(0.6)
                    break
        pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
        time.sleep(0.3)
        kb = kare_al(h)
        baslik = " ".join(t["yazi"] for t in oku.oku(kb, kutu=(bx - 700, by - 14, bx - 100, by + 14), olcek=3))
        bolge = ""
        m_ = re.search(r"([A-Za-zÇĞİÖŞÜçğıöşü]+)\s*B[öo]lges", baslik)
        if m_:
            bolge = m_.group(1)
        return bx, by, kutu, bolge, kb

    def genel_harita_resmi():
        """Genel haritayi (M) acar; (kapat_dugmesi, harita_resmi 254x317, x0, y0) ya da None. Harita acik kalir."""
        kd_ = harita_ac()
        if kd_ is None:
            return None
        time.sleep(0.3)
        pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
        time.sleep(0.15)
        k_ = kare_al(h)
        x0_, y0_ = kd_[0] - 242, kd_[1] + 17
        return kd_, k_[y0_:y0_ + 317, x0_:x0_ + 254].copy(), x0_, y0_

    def kayitli_harita_bul(resim):
        """Genel harita resmini kayitli haritalarla karsilastirir; en benzer kaydin adi (ya da None)."""
        en = None
        for f_ in os.listdir(harita_klasor):
            if not f_.endswith(".png"):
                continue
            r_ = np.array(Image.open(os.path.join(harita_klasor, f_)).convert("RGB"))
            if r_.shape != resim.shape:
                continue
            fark_ = float(np.abs(r_.astype(int) - resim.astype(int)).mean())
            if en is None or fark_ < en[0]:
                en = (fark_, f_[:-4])
        return en[1] if en and en[0] < 30 else None

    def harita_kaydet():
        su_an[0] = "harita_kaydet"
        g_ = genel_harita_resmi()
        if g_ is None:
            print("harita_kaydet: genel harita acilamadi")
            return
        kd_, resim, _, _ = g_
        ad = kayitli_harita_bul(resim)
        if ad is None:                                      # yeni bolge: adini buyuk haritanin basligindan al
            tikla(*kd_)
            time.sleep(0.3)
            r_ = buyuk_harita_ac_uzak()
            if r_ is not None:
                ad = r_[3] or None
                tikla(r_[0], r_[1])
            ad = ad or time.strftime("bolge_%H%M%S")
        else:
            tikla(*kd_)
        Image.fromarray(resim).save(os.path.join(harita_klasor, ad + ".png"))
        print(f"{time.strftime('%H:%M:%S')}  harita kaydedildi: {ad} (panelde 'Harita' penceresinden secilebilir)")

    def harita_git(ad, rx, ry):
        su_an[0] = "harita_git"
        g_ = genel_harita_resmi()
        if g_ is None:
            print("git: genel harita acilamadi")
            return False
        kd_, resim, x0_, y0_ = g_
        burasi = kayitli_harita_bul(resim)
        if ad and burasi and oku.sade(ad) != oku.sade(burasi):
            print(f"{time.strftime('%H:%M:%S')}  git: hedef '{ad}' haritasinda, ben '{burasi}' haritasindayim - once oraya isinlan")
            tikla(*kd_)
            return False
        mh0, _ = mini_harita(kare_al(h))
        tikla(x0_ + rx * 254, y0_ + ry * 317)
        time.sleep(0.6)
        tikla(*kd_)                                       # haritayi kapat (yuruyus devam ediyor)
        yurudu = float(np.abs(mini_harita(kare_al(h))[0] - mh0).mean()) > 1.5
        print(f"{time.strftime('%H:%M:%S')}  git: {ad or burasi or ''} haritasinda isaretlenen noktaya " + ("yuruyor" if yurudu else "YURUYEMEDI (oraya yol yok olabilir)"))
        if not yurudu:
            return False
        bas_, onceki_, durgun_ = time.time(), None, 0
        hz_ = hizli_baslat()
        while time.time() - bas_ < 120 and durum["calis"] and not durum["duraklat"]:     # varana kadar kesmeye ara
            time.sleep(0.5)
            kf_ = kare_al(h)
            if olum_denetle(kf_):
                return False
            if saldiri_altinda():
                print("   git: yolda saldiri - kesmeye donuluyor")
                return False
            if time.time() - bas_ > 3 and (not alan_aktif() or ayar["alana_donerken_dal"]):   # yolda slot: dur, kes
                yk_, gn_ = kf_.shape[:2]
                et_ = [t for t in kirmizi_etiketler(kf_) if math.hypot(t[0] - gn_ // 2, t[1] - yk_ * 0.58) < 450]
                if len(et_) >= ayar["slot_en_az"]:
                    print(f"{time.strftime('%H:%M:%S')}  git: yolda slot goruldu ({len(et_)}) - kesmeye donuluyor")
                    hemen_savas[0] = time.time()
                    return True
            if hizli_adim(hz_, kf_):
                onceki_, durgun_ = None, 0
                continue
            mh_, _ = mini_harita(kf_)
            if onceki_ is not None:
                durgun_ = durgun_ + 1 if float(np.abs(mh_ - onceki_).mean()) < 0.6 else 0
                if durgun_ >= 4:
                    print(f"{time.strftime('%H:%M:%S')}  git: varildi")
                    alan["yerel"] = 0
                    return True
            onceki_ = mh_
        return True

    def buyuk_harita_ac():
        """Buyuk haritayi (M -> Buyuk harita) acar. Donus: (bx, by) X dugmesi ya da None."""
        pencereleri_kapat()
        once = acik_pencereler(kare_al(h), kapat_s)
        pydirectinput.press("m")
        genel = None
        for _ in range(10):
            time.sleep(0.12)
            yeni_ = [q for q in acik_pencereler(kare_al(h), kapat_s) if all(abs(q[0] - o[0]) > 6 or abs(q[1] - o[1]) > 6 for o in once)]
            if yeni_:
                genel = yeni_[0]
                break
        if genel is None:
            return None
        dugme = [t for t in oku.oku(kare_al(h), kutu=(genel[0] - 300, genel[1] + 300, genel[0] + 40, genel[1] + 400), olcek=3)
                 if oku.benzer(t["yazi"], "buyuk harita", 0.75)]
        if not dugme:
            pydirectinput.press("esc")
            return None
        tikla(dugme[0]["x"], dugme[0]["y"])
        for _ in range(12):
            time.sleep(0.12)
            for q in acik_pencereler(kare_al(h), kapat_s):
                if abs(q[0] - genel[0]) > 20 and q[1] < genel[1] + 40 and q[0] > 900:
                    return q
        pydirectinput.press("esc")
        return None

    def npc_yuru(ad_ara, ad_tam):
        """Buyuk haritanin NPC aramasina ad_ara yazar, listede adi ad_tam olan satirin okuna tiklar, varana kadar bekler."""
        b_ = buyuk_harita_ac()
        if b_ is None:
            print("npc_yuru: buyuk harita acilamadi")
            return False
        bx, by = b_
        durum["yazi"] = True                                     # harita kapanana kadar Z basan izlek dursun (kutuya yaziyordu)
        time.sleep(0.3)                                          # izlek o anki turunu bitirsin
        for _deneme in range(3):
            tikla(bx - 190, by + 40)                             # NPC Arama kutusu
            time.sleep(0.2)
            for _ in range(20):                                  # kutudaki yaziyi sil
                _asil_press("backspace")
                time.sleep(0.02)
            for ch in ad_ara:
                _asil_press(ch)
                time.sleep(0.06)
            time.sleep(0.8)
            kutu_yazi = " ".join(t["yazi"] for t in oku.oku(kare_al(h), kutu=(bx - 270, by + 28, bx - 40, by + 54), olcek=3))
            if oku.sade(kutu_yazi).replace(" ", "") == oku.sade(ad_ara):
                break
            print(f"   npc_yuru: arama kutusunda '{kutu_yazi}' var - yeniden yaziliyor")
        satirlar = oku.oku(kare_al(h), kutu=(bx - 260, by + 100, bx - 50, by + 560), olcek=2)
        Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", "npc_arama.png"))

        def kapat_ve_birak():
            tikla(bx - 190, by + 40)                             # kutuyu temizle (odak kutuda kalmasin, tuslar oyuna gitsin)
            for _ in range(20):
                _asil_press("backspace")
                time.sleep(0.02)
            tikla(bx, by)
            time.sleep(0.2)
            durum["yazi"] = False
        print("   npc_yuru: liste: " + " | ".join(t["yazi"] for t in satirlar))
        hedef_ = [t for t in satirlar if " ".join(oku.sade(t["yazi"]).split()) == ad_tam]
        if not hedef_:
            print(f"   npc_yuru: listede '{ad_tam}' yok")
            kapat_ve_birak()
            return False
        mh0, _ = mini_harita(kare_al(h))
        tikla(bx - 14, hedef_[0]["y"])                           # satirin sagindaki ok
        pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
        time.sleep(1.0)
        k_ok = kare_al(h)
        Image.fromarray(k_ok).save(os.path.join(KLASOR, "goruntu", "npc_ok_sonrasi.png"))
        if float(np.abs(mini_harita(k_ok)[0] - mh0).mean()) <= 1.5:
            # yurumedi: ok haritayi NPC'ye kaydirmis olabilir -> harita alaninin ortasina en yakin yesil NPC noktasi
            x0b, y0b, x1b, y1b = bx - 899, by + 25, bx - 300, by + 549
            q_ = k_ok[y0b:y1b, x0b:x1b].astype(int)
            yes_ = ((q_[..., 1] > 180) & (q_[..., 0] < 140) & (q_[..., 2] < 140)).astype(np.uint8)
            n_, _, ist_, mer_ = cv2.connectedComponentsWithStats(yes_, 8)
            orta_ = ((x1b - x0b) / 2, (y1b - y0b) / 2)
            nok = [(mer_[i][0], mer_[i][1]) for i in range(1, n_) if ist_[i][4] >= 3]
            print("   npc_yuru: ok yurutmedi - harita hedef NPC'ye ortalandi, tam ortasina tiklaniyor")
            tikla(x0b + orta_[0], y0b + orta_[1])
            time.sleep(0.8)
        kapat_ve_birak()
        print(f"{time.strftime('%H:%M:%S')}  npc_yuru: '{hedef_[0]['yazi']}' yonune yuruyor")
        bas_, onceki_, durgun_ = time.time(), None, 0
        while time.time() - bas_ < 150 and durum["calis"] and not durum["duraklat"]:
            time.sleep(0.5)
            kf_ = kare_al(h)
            if olum_denetle(kf_):
                return False
            if saldiri_altinda() and can_orani(kf_) < 0.4:
                print("   npc_yuru: yolda saldiri - birakildi")
                return False
            mh_, _ = mini_harita(kf_)
            if onceki_ is not None:
                durgun_ = durgun_ + 1 if float(np.abs(mh_ - onceki_).mean()) < 0.6 else 0
                if durgun_ >= 4 and time.time() - bas_ > 3:
                    yk_c, gn_c = kf_.shape[:2]
                    sohbet = oku.sade(" ".join(t["yazi"] for t in oku.oku(kf_, kutu=(gn_c // 2 - 400, yk_c - 120, gn_c // 2 + 400, yk_c - 40), olcek=2)))
                    if "hedefe var" in sohbet or "hedefe ulas" in sohbet:
                        print(f"{time.strftime('%H:%M:%S')}  npc_yuru: varildi (oyun: istenilen hedefe varildi)")
                        return True
                    print(f"{time.strftime('%H:%M:%S')}  npc_yuru: yolda durdu (varilmadi)")
                    return None                                  # cagiran yeniden denesin
            onceki_ = mh_
        return False

    def npc_ok_git(ad_ara, ad_tam, deneme=4):
        """npc_yuru'yu varilana kadar (yolda durursa) en cok 'deneme' kez tekrarlar."""
        for _ in range(deneme):
            r_ = npc_yuru(ad_ara, ad_tam)
            if r_ is not None:
                return r_
        return False

    def dukkan_al(al):
        """Acik 'Dukkan' penceresinde al={'kirmizi20': n, 'mavi20': m} paket alir (her paket 20 kucuk iksir).
        Onay penceresini okur: yalniz '(K)' kucuk iksir ve 20'lik paket ise Evet, degilse Hayir. Alinan paket sayisi."""
        k_ = kare_al(h)
        yk_, gn_ = k_.shape[:2]
        bs_ = cv2.imread(os.path.join(KLASOR, "sablon", "dukkan_baslik.png"))
        if bs_ is None:
            print("   pot al: sablon\\dukkan_baslik.png yok")
            return 0
        bs_ = cv2.cvtColor(bs_, cv2.COLOR_BGR2RGB)
        for _b in range(12):                                    # NPC'ye uzaktan tiklandiysa once yurur: 6 sn'ye kadar bekle
            _, en_, _, bas_ = cv2.minMaxLoc(cv2.matchTemplate(k_, bs_, cv2.TM_CCOEFF_NORMED))
            if en_ >= 0.8:
                break
            time.sleep(0.5)
            k_ = kare_al(h)
        if en_ < 0.8:
            print(f"   pot al: dukkan penceresi bulunamadi ({en_:.2f})")
            return 0
        x0_, y0_ = max(0, bas_[0] - 60), bas_[1]
        bolge_ = (x0_, y0_, min(gn_, bas_[0] + 200), min(yk_, bas_[1] + 400))
        alinan_ = 0

        for ad_, n_ in al.items():
            sb_ = cv2.imread(os.path.join(KLASOR, "sablon", f"dukkan_{ad_}.png"))
            if sb_ is None or n_ <= 0:
                continue
            sb_ = cv2.cvtColor(sb_, cv2.COLOR_BGR2RGB)
            for _ in range(n_):
                k_ = kare_al(h)
                kes_ = k_[bolge_[1]:bolge_[3], bolge_[0]:bolge_[2]]
                fark_, _, yer_, _ = cv2.minMaxLoc(cv2.matchTemplate(kes_, sb_, cv2.TM_SQDIFF_NORMED))
                if fark_ > 0.06:                                # renkli eslesme: 20'lik ile 200'luk ~0.13 ayrisiyor
                    print(f"   pot al: {ad_} dukkanda bulunamadi (fark {fark_:.3f})")
                    break
                x_h = bolge_[0] + yer_[0] + sb_.shape[1] // 2       # Vedat: saga tiklayinca onaysiz aliyor
                y_h = bolge_[1] + yer_[1] + sb_.shape[0] // 2
                pydirectinput.moveTo(ox_son[0] + int(x_h), ox_son[1] + int(y_h))
                time.sleep(0.3)
                pydirectinput.mouseDown(button="right")
                time.sleep(0.1)
                pydirectinput.mouseUp(button="right")
                time.sleep(0.5)
                pydirectinput.moveTo(ox_son[0] + gn_ // 2, ox_son[1] + int(yk_ * 0.75))   # bilgi kutusu sonraki aramayi ortmesin
                time.sleep(0.3)
                alinan_ += 1
                print(f"{time.strftime('%H:%M:%S')}  pot al: {ad_} 1 paket (20 adet) alindi")
        return alinan_

    def satici_adla(k_):
        """Ekrandaki yesil NPC adlarindan (ad_siniflari) 'Satici' yazanini bulur: (orta_x, ad_alt_y) ya da None."""
        try:
            import ad_siniflari
            for e_ in ad_siniflari.ad_etiketleri(k_):
                if e_["sinif"] != "npc":
                    continue
                kes_ = k_[max(0, e_["y0"] - 4):e_["y1"] + 4, max(0, e_["x0"] - 6):e_["x1"] + 6]
                ad_ = "".join(oku.sade(" ".join(t["yazi"] for t in oku.oku(kes_, olcek=4))).split())
                if ad_ and difflib.SequenceMatcher(None, ad_, "satici").ratio() >= 0.8:
                    return (e_["x0"] + e_["x1"]) // 2, e_["y1"]
        except Exception as e_h:
            print("   satici_adla:", e_h)
        return None

    def satici_resimde(k_, esik=0.62):
        """sablon/npc_satici.png ile (renkli, birkac olcek) ekranda Satici'yi arar: (orta_x, ust_y, eslesme) ya da None."""
        sb_ = cv2.imread(os.path.join(KLASOR, "sablon", "npc_satici.png"))
        if sb_ is None:
            return None
        sb_ = cv2.cvtColor(sb_, cv2.COLOR_BGR2RGB)
        yk_, gn_ = k_.shape[:2]
        alan_ = k_[60:yk_ - 160, :gn_ - 230]
        en_iyi = None
        for o_ in (0.6, 0.75, 0.9, 1.0, 1.15, 1.3, 1.5):
            t_ = cv2.resize(sb_, None, fx=o_, fy=o_)
            if t_.shape[0] >= alan_.shape[0] or t_.shape[1] >= alan_.shape[1]:
                continue
            _, en_, _, yer_ = cv2.minMaxLoc(cv2.matchTemplate(alan_, t_, cv2.TM_CCOEFF_NORMED))
            if en_iyi is None or en_ > en_iyi[2]:
                en_iyi = (yer_[0] + t_.shape[1] // 2, 60 + yer_[1], en_)
        return en_iyi if en_iyi and en_iyi[2] >= esik else None

    def satici_test(al=None):
        """Satin alirken Z/pot izlegi tus basmasin (onay penceresini kapatabiliyor)."""
        ox_g, oy_g, _, _ = istemci_kutusu(h)                   # tiklama koordinatlari: pencerenin guncel yeri
        ox_son[0], ox_son[1] = ox_g, oy_g                       # (toplama kipinde ana dongu bunu guncellemiyordu)
        if not al:
            return _satici_test_ic(al)
        durum["yazi"] = True
        try:
            return _satici_test_ic(al)
        finally:
            durum["yazi"] = False

    def _satici_test_ic(al=None):
        """Saticiya yuru, adina tikla, acilan pencereyi kaydet ve oku; HICBIR SEY SATIN ALMA, Esc ile kapat."""
        su_an[0] = "satici_test"
        birak()
        if not npc_ok_git("sat", "satici"):                    # zaten yanindaysak oyun 'varildi' demeyebilir:
            print("   satici_test: varis mesaji yok - ekrandaki hedef okuna bakiliyor")   # ok gorunurse devam
        etiket = []
        geri_adim = False
        for cevir in range(8):                                   # oyunun turuncu hedef oku NPC'nin tam ustunde
            k_ = kare_al(h)
            yk_, gn_ = k_.shape[:2]
            etiket = [t for t in oku.oku(k_, kutu=(gn_ // 2 - 700, 80, gn_ // 2 + 700, yk_ - 180), olcek=3, renkli=True)
                      if " ".join(oku.sade(t["yazi"]).split()) == "satici"]
            if etiket:
                break
            q_ = k_.astype(int)
            tur_ = ((q_[..., 0] > 230) & (q_[..., 0] - q_[..., 2] > 100)).astype(np.uint8)
            tur_[yk_ - 160:, :] = 0
            tur_[:, gn_ - 260:] = 0
            n_, _, ist_, _ = cv2.connectedComponentsWithStats(cv2.dilate(tur_, np.ones((3, 3), np.uint8)), 8)
            oklar = [ist_[i] for i in range(1, n_) if ist_[i][4] >= 80 and ist_[i][3] > ist_[i][2] * 1.3 and ist_[i][3] >= 25]
            if oklar:
                x_o, y_o, w_o, h_o, _ = max(oklar, key=lambda o: o[4])
                ux, uy = int(x_o + w_o / 2), int(y_o + h_o)
                p_ad = k_[max(0, uy - 8):uy + 32, max(0, ux - 110):ux + 110].astype(int)      # okun altindaki yesil NPC adi
                m_ad = np.where((p_ad[..., 1] > 120) & (p_ad[..., 1] - p_ad[..., 0] > 30) & (p_ad[..., 1] - p_ad[..., 2] > 30),
                                0, 255).astype(np.uint8)
                m_ad = np.pad(m_ad, 10, constant_values=255)
                ad_ok = "".join(oku.sade(" ".join(t["yazi"] for t in oku.oku(np.stack([m_ad] * 3, axis=2), olcek=4))).split())
                print(f"   satici_test: hedef okunun altindaki NPC: '{ad_ok}'")
                if ad_ok.startswith("lv"):                     # 'Lv 18 ...' oyuncu etiketi (cogunlukla bizimki): NPC adi degil
                    ad_ok = ""
                if not ad_ok and not geri_adim and math.hypot(ux - gn_ // 2, uy - yk_ * 0.45) < 160:
                    geri_adim = True                             # NPC ustumuzde: adi bizimkinin altinda, bir adim geri
                    print("   satici_test: NPC tam ustumuzde - bir adim geri cekiliyor")
                    tikla(gn_ // 2, int(yk_ * 0.80))
                    time.sleep(1.4)
                    continue
                if ad_ok and difflib.SequenceMatcher(None, ad_ok, "satici").ratio() >= 0.7:
                    etiket = [{"x": ux, "y": uy, "yazi": "hedef oku"}]
                elif not ad_ok:                                  # ad okunamadi: oyunun hedef okuna guven
                    print("   satici_test: ad okunamadi - oyunun hedef okuna guveniliyor")
                    etiket = [{"x": ux, "y": uy, "yazi": "hedef oku"}]
                else:
                    etiket = []
                    print("   satici_test: okun altindaki NPC Satici degil - tiklanmiyor")
                break
            y_s = satici_adla(k_)                                # ok yok: yesil NPC adlarindan 'Satici'yi ara
            if y_s:
                print(f"   satici_test: satici yesil adindan bulundu ({y_s[0]},{y_s[1]})")
                etiket = [{"x": y_s[0], "y": y_s[1] - 10, "yazi": "hedef oku"}]
                break
            pydirectinput.keyDown(ayar["kamera_tusu"])
            time.sleep(0.35)
            pydirectinput.keyUp(ayar["kamera_tusu"])
            time.sleep(0.3)
        Image.fromarray(k_).save(os.path.join(KLASOR, "goruntu", "satici_varis.png"))
        print("   satici_test: ekranda: " + " | ".join(f"{t['yazi']}@({t['x']},{t['y']})" for t in etiket) + f" ({cevir} kez kamera cevrildi)")
        if not etiket:
            return
        e_ = min(etiket, key=lambda t: math.hypot(t["x"] - gn_ // 2, t["y"] - yk_ * 0.5))
        sablon_npc = None
        if al:                                                  # satin alma: dukkan acilana kadar govdenin farkli yerlerine
            bs_d = cv2.imread(os.path.join(KLASOR, "sablon", "dukkan_baslik.png"))   # (ustunde atli oyuncu olabilir)
            bs_d = cv2.cvtColor(bs_d, cv2.COLOR_BGR2RGB) if bs_d is not None else None
            for dx_, dy_ in ((0, 70), (-22, 85), (22, 85), (0, 110), (-28, 55), (28, 55), (0, 40)):
                tikla(e_["x"] + dx_, e_["y"] + dy_)
                acik_ = False
                for _b in range(7):                             # uzaktaysa once yurur
                    time.sleep(0.5)
                    if bs_d is not None and cv2.minMaxLoc(cv2.matchTemplate(kare_al(h), bs_d, cv2.TM_CCOEFF_NORMED))[1] >= 0.8:
                        acik_ = True
                        break
                if acik_:
                    print(f"   pot al: dukkan acildi (tiklama {dx_:+d},{dy_:+d})")
                    break
                pydirectinput.press("esc")                      # yanlis sey acildiysa kapat
                time.sleep(0.3)
        else:
            for alt_ in ((70, 100, 45) if e_["yazi"] == "hedef oku" else (55, 85, 30)):
                tikla(e_["x"], e_["y"] + alt_)
                time.sleep(1.3)
                k2 = kare_al(h)
                if float(np.abs(k2.astype(int) - k_.astype(int)).mean()) > 6:
                    sablon_npc = k_[max(0, e_["y"] + 5):e_["y"] + 175, max(0, e_["x"] - 50):e_["x"] + 50]
                    break
        pydirectinput.moveTo(ox_son[0] + 300, ox_son[1] + 900)
        time.sleep(0.4)
        k2 = kare_al(h)
        Image.fromarray(k2).save(os.path.join(KLASOR, "goruntu", "satici_pencere.png"))
        if sablon_npc is not None and sablon_npc.size:              # satici gorunusu: sonra resminden tanimak icin
            Image.fromarray(sablon_npc).save(os.path.join(KLASOR, "sablon", "npc_satici.png"))
            print("   satici_test: saticinin resmi sablon/npc_satici.png olarak kaydedildi")
        print("   satici_test: pencere: " + " | ".join(t["yazi"] for t in oku.oku(k2, kutu=(gn_ // 2 - 500, 60, gn_ // 2 + 500, yk_ - 150), olcek=2))[:600])
        if al:
            n_al = dukkan_al(al)
            print(f"{time.strftime('%H:%M:%S')}  pot al: toplam {n_al} paket alindi")
            pot_alim[0] = time.time()
            if n_al:
                pot_bitti[0] = 0.0
                pot_yasak[0] = 0.0                               # yuvalar yeniden doldurulsun
        for _ in range(2):
            pydirectinput.press("esc")
            time.sleep(0.3)
        return n_al if al else True

    def uzaktan(kapaniyor=False):
        """Panelden/uzaktan gelen komutu (komut.json) uygular; canli.json'a durumu yazar (2 sn'de bir)."""
        if not kapaniyor and time.time() - canli["son"] < 2:
            return
        canli["son"] = time.time()
        with canli["kilit"]:
            _uzaktan_is(kapaniyor)

    def _uzaktan_is(kapaniyor):
        try:
            if os.path.exists(yol_komut):
                with open(yol_komut, encoding="utf-8-sig") as f:
                    kj_ = json.load(f)
                k_ = kj_.get("komut", "")
                if k_ == "git":
                    istek["git"] = (kj_.get("harita", ""), float(kj_.get("x", 0.5)), float(kj_.get("y", 0.5)))
                elif k_ == "harita_kaydet":
                    istek["harita_kaydet"] = True
                os.remove(yol_komut)
                if k_ == "duraklat":
                    durum["duraklat"] = True
                elif k_ == "devam":
                    durum["duraklat"] = False
                elif k_ == "kapat":
                    durum["calis"] = False
                elif k_ == "bayrak_test":
                    istek["bayrak_test"] = ()
                elif k_ == "bayrak_test2":
                    istek["bayrak_test"] = ("jinno",)
                elif k_ in ("koy1", "koy2"):
                    istek["isinlan"] = ayar["koyler"][0 if k_ == "koy1" else 1]
                elif k_ == "yuru_test":
                    istek["yuru_test"] = True
                elif k_ == "yuru_test2":
                    istek["yuru_test"] = True
                    istek["yuru_test_kapat"] = True
                elif k_ == "buyuk_harita_test":
                    istek["buyuk_harita"] = True
                elif k_ == "satici_test":
                    istek["satici_test"] = True
                elif k_ == "pot_al":
                    istek["pot_al"] = True
                    open(os.path.join(KLASOR, "pot_al.istek"), "w").close()   # bot yeniden acilsa da unutulmasin
                elif k_ == "kamera_test":
                    istek["kamera_test"] = True
                elif k_ == "binek_test":
                    istek["binek_test"] = True
                elif k_ == "beceri_goruntu":
                    istek["beceri_goruntu"] = True
                elif k_ == "arka_test":
                    threading.Thread(target=arka_test, daemon=True).start()
                print(f"{time.strftime('%H:%M:%S')}  uzaktan komut: {k_}")
            with open(yol_canli + ".tmp", "w", encoding="utf-8") as f:
                json.dump({"zaman": time.time(), "calisiyor": bool(durum["calis"]) and not kapaniyor,
                           "duraklat": durum["duraklat"], "oyun_onde": win32gui.GetForegroundWindow() == h,
                           "profil": ayar.get("profil", "ozel"), "seviye": benim_sev, "kesilen": kesilen, "exp_saat": exp_toplam[2], "pot_bitti": time.time() - pot_bitti[0] < 1800,
                           "baslangic": canli["baslangic"], "av_hedefi": list(av_aranan),
                           "aranan": list(aranan_durum), "plan": plan["p"].get("yazi", ""), "esya": esya_yazi}, f, ensure_ascii=False)
            os.replace(yol_canli + ".tmp", yol_canli)
        except Exception as e_:
            if not isinstance(e_, PermissionError):
                print("uzaktan:", e_)

    def _uzaktan_dongu():                   # ana dongu uzun bir iste (yuruyus, konusma) iken de calisir
        while durum["calis"]:
            uzaktan()
            time.sleep(1.0)

    threading.Thread(target=_uzaktan_dongu, daemon=True).start()

    secilemedi = 0
    son_serbest, tehdit = 0.0, False
    yol_m = os.path.join(KLASOR, "sablon", "market_baslik.png")
    market_s = cv2.imread(yol_m, cv2.IMREAD_GRAYSCALE) if os.path.exists(yol_m) else None
    sev_gorulen = []              # (zaman, seviye): son gorulen yaratik seviyeleri -> bolge hafizasi
    yog_gorulen = []              # (zaman, ekrandaki uygun canavar sayisi) -> bolge kalabaligi
    istek = {}                    # panelden gelen ve oyunda tiklama gerektiren tek seferlik isler
    if os.path.exists(os.path.join(KLASOR, "pot_al.istek")):        # yeniden acilmadan once gelmis pot alma istegi
        istek["pot_al"] = True
    ad_gorulen = []               # (zaman, yaratik adi): ekranda okunan adlar -> bolge hafizasi
    son_av = [time.time(), 0.0]   # [av yaratigi son gorulme, son "av bolgesine git" denemesi]
    bilgi = bilgi_yukle()
    esya_secim = esya_tablosu_bul(ayar["esya_avi"]) if ayar["esya_avi"] else None
    esya_hedef = [k_["ad"] for k_ in (esya_secim or {}).get("kaynaklar", []) if k_.get("tur") != "metin"]
    esya_yazi = ""
    if esya_secim:
        if any(k_.get("tur") == "metin" for k_ in esya_secim.get("kaynaklar", [])):
            ayar["metin_kes"] = True
        esya_yazi = (f"{esya_secim['ad']} <- " + ", ".join(f"{k_['ad']} (Lv {k_.get('lv', '?')}, {k_.get('harita', '?')})"
                                                  for k_ in esya_secim.get("kaynaklar", [])))
        print(f"{time.strftime('%H:%M:%S')}  esya avi: {esya_yazi}")
    elif ayar["esya_avi"]:
        print(f"{time.strftime('%H:%M:%S')}  esya avi: '{ayar['esya_avi']}' tabloda yok")
    oto = {"acik": False, "bas": None, "kacti": 0, "tuttu": 0}    # saldiri tusu basiliyken oyun yeni hedefi kendi seciyor mu
    olum_gorulen = [None]

    def _olum_bekci():
        """Ana dongu uzun bir iste (NPC'ye yuruyus, konusma, gezinme) iken olunce de kalkilsin."""
        while durum["calis"]:
            time.sleep(1.5)
            try:
                if (durum["duraklat"] or olum_s is None or not ayar["olunce_yeniden_basla"]
                        or win32gui.GetForegroundWindow() != h):
                    continue
                k_ = kare_al(h)
                p_ = olum_penceresi(k_)
                if p_ is None:
                    olum_gorulen[0] = None
                    olum_yok_goruldu()
                    continue
                olum_gorulen[0] = olum_gorulen[0] or time.time()
                if time.time() - olum_gorulen[0] > 5:           # ana dongu 5 sn icinde kaldirmadi: bekci tiklar
                    if not olum_kilit.acquire(blocking=False):  # ana dongu su an tikliyor
                        continue
                    try:
                        sehirde_ = olum_karari()                # ayni olumse ana dongunun karari korunur
                        if olum_pencere["yeni"]:
                            olum_yaz(k_, sehirde_, " [olum bekcisi]")
                        else:
                            print(f"{time.strftime('%H:%M:%S')}  olum bekcisi: '{'Sehirde' if sehirde_ else 'Burada'} "
                                  f"yeniden basla' (eslesme {p_[0]:.2f})")
                        Image.fromarray(k_).save(os.path.join(KLASOR, "goruntu", "olum_bekci.png"))
                        birak()
                        if diril_tikla(p_[1], sehirde_, "olum bekcisi"):
                            if sehirde_:
                                sehirden_cik[0] = True
                            iksir_yenile()
                        olum_gorulen[0] = None
                    finally:
                        olum_kilit.release()
                    time.sleep(3)
            except Exception as e_:
                print("olum bekcisi:", e_)

    if not ayar["sadece_toplama"]:
        threading.Thread(target=_olum_bekci, daemon=True).start()

    _yolo["ayar"] = ayar

    def _sekil_izlegi():
        """YOLO sekil modeli: en son kareyi olculen sureye gore (en az 150 ms ara) modele verir."""
        gpu_ = gpu_aday_ = None
        try:
            import sekil as sekil_mod
            if ayar.get("yolo_gpu", True) and ayar.get("yolo_kullan", True):
                gpu_aday_ = sekil_mod.GpuIstemci(20.0)
                gpu_ = gpu_aday_ if gpu_aday_.ok else None
                if not gpu_:
                    print("sekil: GPU sunucu yok - CPU yoluna donuluyor (hazir olursa gecilir)")
            model_ = None if gpu_ else sekil_mod.Sekil()
        except Exception:
            return
        if gpu_:
            print("sekil: GPU sunucu hazir")
            _yolo["sag"] = "GPU-sunucu"
            son_kare_ = None
            while durum["calis"]:
                time.sleep(0.03)
                try:
                    if (not ayar.get("yolo_kullan", True) or durum["duraklat"]
                            or win32gui.GetForegroundWindow() != h):
                        continue
                    k_ = _son_kare[0]
                    if k_ is not None and k_ is not son_kare_ and time.time() - _yolo["kare_t"] <= 1.0:
                        son_kare_ = k_
                        gpu_.yaz(k_)
                    o_ = gpu_.oku()
                    if o_:
                        _yolo["kutular"], _yolo["t"], _yolo["ms"] = o_[0], time.time(), o_[1]
                        _yolo["uc_ms"] = o_[2]
                        _yolo.setdefault("ist", []).append((o_[1], o_[2]))
                        if len(_yolo["ist"]) >= 150:
                            a_ = _yolo["ist"]
                            print(f"{time.strftime('%H:%M:%S')}  sekil GPU: sunucu {sum(x[0] for x in a_) / len(a_):.1f} ms, uctan uca {sum(x[1] for x in a_) / len(a_):.0f} ms (n={len(a_)})")
                            _yolo["ist"] = []
                except Exception as e_:
                    print("sekil gpu izlegi:", e_)
                    time.sleep(2)
            return
        if not model_.ok:
            print("sekil: model/onnxruntime yok - devre disi")
            return
        _yolo["sag"] = model_.saglayici
        print(f"sekil: hazir ({model_.saglayici})")
        son_kare_ = None
        son_gpu_kontrol_ = time.time()
        while durum["calis"]:
            time.sleep(max(0.15, _yolo["ms"] / 1000.0))
            try:
                if gpu_aday_ is not None and time.time() - son_gpu_kontrol_ > 5:
                    son_gpu_kontrol_ = time.time()
                    if ayar.get("yolo_gpu", True) and gpu_aday_._hazir():
                        gpu_aday_.ok = True
                        print("sekil: GPU sunucu hazir - GPU'ya gecildi")
                        _yolo["sag"] = "GPU-sunucu"
                        son_k2_ = None
                        while durum["calis"]:
                            time.sleep(0.03)
                            if (not ayar.get("yolo_kullan", True) or durum["duraklat"]
                                    or win32gui.GetForegroundWindow() != h):
                                continue
                            k2_ = _son_kare[0]
                            if k2_ is not None and k2_ is not son_k2_ and time.time() - _yolo["kare_t"] <= 1.0:
                                son_k2_ = k2_
                                gpu_aday_.yaz(k2_)
                            o2_ = gpu_aday_.oku()
                            if o2_:
                                _yolo["kutular"], _yolo["t"], _yolo["ms"] = o2_[0], time.time(), o2_[1]
                                _yolo["uc_ms"] = o2_[2]
                                _yolo.setdefault("ist", []).append((o2_[1], o2_[2]))
                                if len(_yolo["ist"]) >= 150:
                                    a_ = _yolo["ist"]
                                    print(f"{time.strftime('%H:%M:%S')}  sekil GPU: sunucu {sum(x[0] for x in a_) / len(a_):.1f} ms, uctan uca {sum(x[1] for x in a_) / len(a_):.0f} ms (n={len(a_)})")
                                    _yolo["ist"] = []
                        return
                if (not ayar.get("yolo_kullan", True) or durum["duraklat"]
                        or win32gui.GetForegroundWindow() != h):
                    continue
                k_ = _son_kare[0]
                if k_ is None or k_ is son_kare_ or time.time() - _yolo["kare_t"] > 1.0:
                    continue
                son_kare_ = k_
                t0_ = time.time()
                kut_ = model_.tespit(k_, 0.25)
                _yolo["ms"] = (time.time() - t0_) * 1000.0
                _yolo["kutular"], _yolo["t"] = kut_, time.time()
            except Exception as e_:
                print("sekil izlegi:", e_)
                time.sleep(2)

    threading.Thread(target=_sekil_izlegi, daemon=True).start()
    def _durgun_bekci():
        """Karakter 3 sn'den uzun hem yurumuyor (mini harita sabit) hem vurmuyorsa (hedef cani degismiyor)
        ne yapildigini bir kez loga yazar."""
        son_aktif, onceki_mh, onceki_hc, yazildi = time.time(), None, None, False
        while durum["calis"]:
            time.sleep(0.5)
            try:
                if durum["duraklat"] or win32gui.GetForegroundWindow() != h:
                    son_aktif, yazildi = time.time(), False
                    continue
                k_ = kare_al(h)
                mh_, _ = mini_harita(k_)
                hc_ = hedef_cani(k_)
                yuruyor = onceki_mh is not None and float(np.abs(mh_ - onceki_mh).mean()) > 0.6
                vuruyor = onceki_hc is not None and hc_ > 0.03 and abs(hc_ - onceki_hc) > 0.005
                onceki_mh, onceki_hc = mh_, hc_
                if yuruyor or vuruyor:
                    if yazildi:
                        print(f"   DURAKLAMA bitti ({time.time() - son_aktif:.1f} sn)")
                    son_aktif, yazildi = time.time(), False
                elif not yazildi and time.time() - son_aktif > 3:
                    yazildi = True
                    print(f"{time.strftime('%H:%M:%S')}  DURAKLAMA >3 sn: su an '{su_an[0]}'")
            except Exception:
                pass

    can_gecmis = []

    def saldiri_altinda():
        """Son 2.5 sn'de can %3'ten fazla dustu mu (birisi vuruyor)."""
        simdi_ = time.time()
        son_ = [c_ for t_, c_ in can_gecmis if simdi_ - t_ < 2.5]
        return len(son_) >= 3 and max(son_) - son_[-1] >= 0.03

    def _pot_toplama_izlegi():
        """Her modda: yere dusenleri toplamak icin Z'ye surekli basar; can/mana dusunce hemen pot basar."""
        son_z, pot_s = 0.0, [0.0, 0.0]
        while durum["calis"]:
            time.sleep(0.1)
            try:
                if (durum["duraklat"] or durum.get("yazi") or win32gui.GetForegroundWindow() != h
                        or time.time() - giris.get("ekranda", 0) < 8):
                    continue
                if ayar["esyaya_tikla"] and time.time() - son_z > ayar["toplama_araligi_sn"]:
                    _asil_press(ayar["toplama_tusu"])
                    son_z = time.time()
                k_p = kare_al(h)
                can_p = can_orani(k_p)
                if can_p >= 0.02:
                    can_gecmis.append((time.time(), can_p))
                    del can_gecmis[:-40]
                if 0.02 <= can_p < ayar["can_esigi"] and time.time() - pot_s[0] > 0.3:
                    _asil_press(ayar["can_potu_tusu"])                    # kirmizi pot
                    pot_s[0] = time.time()
                if (ayar["mana_potu_tusu"] and can_p >= 0.02 and mana_orani(k_p) < ayar["mana_esigi"]
                        and time.time() - pot_s[1] > 0.3):
                    _asil_press(ayar["mana_potu_tusu"])                   # mavi pot
                    pot_s[1] = time.time()
            except Exception:
                pass

    threading.Thread(target=_pot_toplama_izlegi, daemon=True).start()

    if not ayar["sadece_toplama"]:
        threading.Thread(target=_durgun_bekci, daemon=True).start()
    aranan_durum[:] = durum_oku().get("aranan", [])
    son_aranan_tarama, son_aranan_log = 0.0, 0.0
    try:
        pot_son = [0.0, 0.0]
        if ayar["sadece_toplama"]:
            print(time.strftime("%H:%M:%S") + "  YALNIZ OTOMATIK TOPLAMA: " + ayar["toplama_tusu"].upper()
                  + " tusuna surekli basiliyor, can/mana dusunce kirmizi/mavi pot basiliyor; baska hicbir sey yapilmiyor")
        while durum["calis"] and ayar["sadece_toplama"]:
            uzaktan()
            if istek.get("pot_al") and not durum["duraklat"] and win32gui.GetForegroundWindow() == h:
                istek.pop("pot_al")                             # toplama kipinde de pot alinabilsin (yerinde dururken)
                try:
                    os.remove(os.path.join(KLASOR, "pot_al.istek"))
                except OSError:
                    pass
                pot_alim[0] = time.time()
                print(f"{time.strftime('%H:%M:%S')}  pot al: saticiya gidiliyor (toplama kipi)")
                satici_test(al={"kirmizi20": ayar["pot_al_kirmizi_paket"], "mavi20": ayar["pot_al_mavi_paket"]})
                continue
            if time.time() - son_damga_bakis > 5:
                son_damga_bakis = time.time()
                if kod_damgasi() != ilk_damga and kod_saglam():
                    yeniden_baslat[0] = True
                    break
            if not durum["duraklat"] and win32gui.GetForegroundWindow() == h:
                pot_yuvasi_doldur(kare_al(h))
            if False:                                    # Z ve pot artik _pot_toplama_izlegi'nde (her modda)
                k_t = kare_al(h)
                can_t = can_orani(k_t)
                if 0.02 <= can_t < ayar["can_esigi"] and time.time() - pot_son[0] > 0.5:
                    pydirectinput.press(ayar["can_potu_tusu"])          # kirmizi pot
                    pot_son[0] = time.time()
                if (ayar["mana_potu_tusu"] and can_t >= 0.02 and mana_orani(k_t) < ayar["mana_esigi"]
                        and time.time() - pot_son[1] > 0.5):
                    pydirectinput.press(ayar["mana_potu_tusu"])         # mavi pot
                    pot_son[1] = time.time()
            time.sleep(ayar["toplama_araligi_sn"])
        while durum["calis"] and not ayar["sadece_toplama"] and not yeniden_baslat[0]:
            uzaktan()
            if durum["duraklat"] or win32gui.GetForegroundWindow() != h:
                birak()
                time.sleep(0.4)
                continue
            kare = kare_al(h)
            ox, oy, gen, yuk = istemci_kutusu(h)
            su_an[0] = "ana dongu (hedef ariyor)"
            ox_son[0], ox_son[1] = ox, oy
            if time.time() - son_damga_bakis > 5:
                son_damga_bakis = time.time()
                if kod_damgasi() != ilk_damga and kod_saglam():
                    print(f"{time.strftime('%H:%M:%S')}  yeni surum bulundu - bot kendini yeniden baslatiyor")
                    birak()
                    yeniden_baslat[0] = True
                    break
            if ayar["yeniden_baglan"] and giris_denetle(kare):
                continue
            if olum_denetle(kare):
                continue
            if engel_kac[0] and not saldiri_altinda():
                engel_kac[0] = False
                try:
                    gezin()
                except Exception as e_ek:
                    print("engel kac:", e_ek)
                continue
            if alan_don[0] and not saldiri_altinda():
                alan_don[0] = False
                if len(kirmizi_etiketler(kare)) >= 2:          # etrafta yaratik var: once onlari kes, haritaya gitme
                    son_gezin[0] = time.time() - ayar["gezin_bekle_sn"]
                    continue
                try:
                    gezin()
                except Exception as e_ad:
                    print("alan donus:", e_ad)
                continue
            if sehirden_cik[0]:                                # sehirde dirildi: koyden disari, uygun bolgeye
                sehirden_cik[0] = False
                print(f"{time.strftime('%H:%M:%S')}  sehirde dirildi - koyden disari yuruyor (temkin {ayar['temkin_dk']} dk)")
                time.sleep(2.0)
                gezin()
                continue
            if sohbet_s is not None and simge_bul(kare[yuk - 120:, gen // 2 - 400:gen // 2 + 400], sohbet_s, 0.85) is not None:
                pydirectinput.press("esc")                      # sohbet yazma kutusu acik kalmis
                time.sleep(0.2)
            if market_s is not None and simge_bul(kare, market_s, 0.9) is not None:
                print(f"{time.strftime('%H:%M:%S')}  KORUMA: Nesne Market acik - Esc ile kapatiliyor (satin alma yok)")
                birak()
                for _ in range(3):
                    pydirectinput.press("esc")
                    time.sleep(0.25)
                continue
            # tehdit: dibimde yaratik var -> gorev/envanter/yazi okuma gibi isler ertelenir, hemen vurulur
            # (45 sn kesintisiz tehditte bir tur islere izin verilir ki iksir/gorev tamamen aksamasin)
            _yakin = any(math.hypot(t[0] - gen // 2, t[1] - (int(yuk * 0.58) - 110)) < ayar["saldiran_yaricapi_piksel"]
                         for t in kirmizi_etiketler(kare))
            if not _yakin or time.time() - son_serbest > 45:
                son_serbest, tehdit = time.time(), False
            else:
                tehdit = True
            if time.time() - hemen_savas[0] < ayar["dalinca_hemen_sn"]:
                tehdit = True                                   # slota yeni dalindi: once vur, yan isler sonra
            # izleme: arada bir kare kaydet (gorev penceresi, olum ekrani gibi durumlari sonradan gormek icin)
            # sekil modeli (YOLO) icin egitim karesi: oyun ekrani, arayuz acik pencere yokken
            if ayar["yolo_veri_sn"] and time.time() - son_yolo_veri[0] > ayar["yolo_veri_sn"]:
                son_yolo_veri[0] = time.time()
                try:
                    vk = os.path.join(KLASOR, "veri_yolo", "ham")
                    os.makedirs(vk, exist_ok=True)
                    if len(os.listdir(vk)) < ayar["yolo_veri_en_cok"] and kirmizi_etiketler(kare):
                        Image.fromarray(kare).save(os.path.join(vk, time.strftime("%Y%m%d_%H%M%S") + ".jpg"), quality=93)
                        _kare_paylas(kare, ayar)
                except Exception as e_y:
                    print("yolo veri:", e_y)
            if time.time() - son_izleme > ayar["izleme_araligi_sn"]:
                son_izleme = time.time()
                izk = os.path.join(KLASOR, "goruntu", "izleme")
                os.makedirs(izk, exist_ok=True)
                Image.fromarray(kare).save(os.path.join(izk, time.strftime("%Y%m%d_%H%M%S") + ".jpg"), quality=85)
                eskiler = sorted(os.listdir(izk))[:-80]
                for f in eskiler:
                    os.remove(os.path.join(izk, f))
            can = can_orani(kare)
            if can < 0.02:
                olu_kare += 1
                if olu_kare == 2:
                    Image.fromarray(kare).save(os.path.join(KLASOR, "goruntu", "can_sifir_son.png"))
                if olu_kare >= ayar["olum_kare_siniri"]:
                    Image.fromarray(kare).save(os.path.join(KLASOR, "goruntu", "olum.png"))
                    olum_deneme += 1
                    dugme = None
                    if diyalog_acik(kare, orta_parlaklik(kare)):    # gorev penceresi arayuzu (can cubugunu) gizler
                        print(f"{time.strftime('%H:%M:%S')}  can cubugu gizli: acik pencere var - ilerletiliyor")
                        diyalog_ilerlet([], "npc_gorev", orta_parlaklik(kare))
                        olu_kare, olum_deneme = 0, 0
                        continue
                    if ayar["olunce_yeniden_basla"]:
                        birak()
                        satirlar = oku.oku(kare, olcek=2)
                        dugme = [t for t in satirlar if oku.benzer(t["yazi"], "burada")]
                    if dugme:
                        print(f"{time.strftime('%H:%M:%S')}  olum: '{dugme[0]['yazi']}' dugmesine tiklaniyor")
                        tikla(dugme[0]["x"], dugme[0]["y"])
                        time.sleep(3)
                        olu_kare = 0
                        continue
                    if olum_deneme >= 1:                            # olum penceresi degil (o sablonla ayrica yakalanir): pencereyi Esc ile kapat
                        print(f"{time.strftime('%H:%M:%S')}  can sifir gorunuyor, dugme yok - Esc ile pencereler kapatilip devam")
                        Image.fromarray(kare).save(os.path.join(KLASOR, "goruntu", "can_sifir_bilinmeyen.png"))
                        pydirectinput.press("esc")
                        olu_kare, olum_deneme = 0, 0
                    time.sleep(2)
                    continue
            else:
                olu_kare = 0
                olum_deneme = 0
            if 0.02 <= can < ayar["can_esigi"]:
                pydirectinput.press(ayar["can_potu_tusu"])
            if ayar["mana_potu_tusu"] and mana_orani(kare) < ayar["mana_esigi"]:
                pydirectinput.press(ayar["mana_potu_tusu"])

            # hizli cubuk 1. sayfada degilse (pot ve beceri tuslari calismaz) geri al
            if sayfa_s is not None and time.time() - son_sayfa > 3:
                son_sayfa = time.time()
                bolge = cv2.cvtColor(kare[yuk - 40:yuk - 8, gen // 2 + 220:gen // 2 + 260], cv2.COLOR_RGB2GRAY)
                r_s = cv2.matchTemplate(bolge, sayfa_s, cv2.TM_CCOEFF_NORMED)
                _, en_s, _, yer_s = cv2.minMaxLoc(r_s)
                if en_s < 0.86:
                    print(f"{time.strftime('%H:%M:%S')}  hizli cubuk 1. sayfada degil - duzeltiliyor")
                    tikla(gen // 2 + 239, yuk - 33)          # sayfa oku
                    time.sleep(0.4)
                    pydirectinput.moveTo(ox + gen // 2, oy + int(yuk * 0.75))
                    continue

            # guclendirme becerileri (hava kilici, ofke): sonunce yeniden yak
            guc_denetle(kare)

            # acik kalmis NPC konusmasi (or. bot yeniden acilirken yarim kaldi): dugmeleriyle ilerlet
            if not tehdit and time.time() - son_diyalog_bakis > 20:
                son_diyalog_bakis = time.time()
                if diyalog_acik(kare, orta_parlaklik(kare)):
                    print(f"{time.strftime('%H:%M:%S')}  acik konusma penceresi bulundu - ilerletiliyor")
                    diyalog_ilerlet([], "npc_gorev", orta_parlaklik(kare))
                    continue

            # kamera egimi: duzenli olarak yatay aciya getir (G tepeye diker, T yataylastirir)
            if ayar["kamera_egim_t_sn"] and time.time() - son_kamera_egim[0] > ayar["kamera_egim_aralik_sn"] and sakin_mi(kare):
                kamera_egim_ayarla()
                continue

            # kamera hep en uzakta kalsin (cadir/agac yakinlastirirsa geri al)
            if ayar["kamera_uzak_tusu"] and time.time() - son_kamera_uzak > ayar["kamera_uzak_aralik_sn"]:
                son_kamera_uzak = time.time()
                pydirectinput.keyDown(ayar["kamera_uzak_tusu"])
                time.sleep(1.2)
                pydirectinput.keyUp(ayar["kamera_uzak_tusu"])

            # egitmen: bir kereligine haritadan egitmeni bul, git, beceri grubunu sec
            if egitim_gerek and not tehdit:
                egitim_gerek = False
                try:
                    sonuc_e = egitmene_git()
                    print("egitmen: sonuc =", sonuc_e)
                    durum_yaz(egitmen_denendi=True, egitmen_sonuc=bool(sonuc_e), zaman=time.strftime("%Y-%m-%d %H:%M:%S"))
                except Exception:
                    import traceback
                    traceback.print_exc()
                continue

            # beceri puani: acilista ve her seviye atlayista dagit
            if not tehdit and pot_yuvasi_doldur(kare):
                continue
            if istek.get("yuru_test") and not tehdit:
                istek.pop("yuru_test")
                birak()
                yuru_test()
                continue
            if istek.get("git") and not (tehdit and saldiri_altinda()):
                hedef_g = istek.pop("git")
                birak()
                harita_git(*hedef_g)
                continue
            if istek.get("harita_kaydet") and not tehdit:
                istek.pop("harita_kaydet")
                harita_kaydet()
                continue
            if istek.get("binek_test"):                      # at muhrune sag tikla: once/sonra kareleri
                istek.pop("binek_test")
                birak()
                Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", "binek_0.png"))
                pydirectinput.press(ayar["envanter_tusu"])
                time.sleep(0.5)
                k_b = kare_al(h)
                yer_b = esya_bul(k_b, cv2.cvtColor(cv2.imread(os.path.join(KLASOR, "sablon", "binek.png")), cv2.COLOR_BGR2RGB))
                print(f"{time.strftime('%H:%M:%S')}  binek_test: at muhru {'bulundu ' + str(yer_b) if yer_b else 'BULUNAMADI'}")
                if yer_b:
                    pydirectinput.moveTo(ox + yer_b[0], oy + yer_b[1])
                    time.sleep(0.15)
                    pydirectinput.click(button="right")
                    time.sleep(2.5)
                pydirectinput.press(ayar["envanter_tusu"])
                time.sleep(0.4)
                Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", "binek_1.png"))
                pydirectinput.moveTo(ox + gen // 2, oy + int(yuk * 0.4))
                pydirectinput.click()                             # biraz yuru: hiz farki gorulsun
                time.sleep(1.5)
                Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", "binek_2.png"))
                continue
            if istek.get("kamera_test"):                     # hangi tus kamerayi egiyor: kareleri kaydet
                istek.pop("kamera_test")
                birak()
                Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", "kamera_0.png"))
                for ad_t, tus_t, sn_t in (("g", "g", 0.5), ("t", "t", 1.0), ("t2", "g", 0.5)):
                    pydirectinput.keyDown(tus_t)
                    time.sleep(sn_t)
                    pydirectinput.keyUp(tus_t)
                    time.sleep(0.4)
                    Image.fromarray(kare_al(h)).save(os.path.join(KLASOR, "goruntu", f"kamera_{ad_t}.png"))
                print(f"{time.strftime('%H:%M:%S')}  kamera_test: kareler kaydedildi (g 0.5 / t 1.0 / g 0.5)")
                continue
            if istek.get("satici_test") and not tehdit:
                istek.pop("satici_test")
                satici_test()
                continue
            if (ayar["pot_satin_al"] and not tehdit and time.time() - pot_bitti[0] < 1800
                    and time.time() - pot_alim[0] > 1200):          # can potu bitti: koydeki saticidan al
                istek["pot_al"] = True
            if istek.get("pot_al") and not tehdit:
                istek.pop("pot_al")
                try:
                    os.remove(os.path.join(KLASOR, "pot_al.istek"))
                except OSError:
                    pass
                pot_alim[0] = time.time()
                print(f"{time.strftime('%H:%M:%S')}  pot al: saticiya gidiliyor")
                n_p = satici_test(al={"kirmizi20": ayar["pot_al_kirmizi_paket"], "mavi20": ayar["pot_al_mavi_paket"]})
                if n_p is None and not istek.pop("pot_koy_denendi", False):
                    print(f"{time.strftime('%H:%M:%S')}  pot al: bu haritada Satici bulunamadi - koye isinlanip yeniden denenecek")
                    istek["pot_koy_denendi"] = True
                    istek["pot_al_sonra"] = True
                    istek["isinlan"] = ayar["koyler"][0]
                else:
                    istek.pop("pot_koy_denendi", None)
                continue
            if istek.get("buyuk_harita") and not tehdit:
                istek.pop("buyuk_harita")
                buyuk_harita_dene()
                continue
            if istek.get("isinlan") and not tehdit:
                koy_ = istek.pop("isinlan")
                birak()
                bayrak_dene((ayar["imparatorluk"], koy_), sec=True)
                if istek.pop("pot_al_sonra", False):              # pot almak icin koye gelindi: simdi saticiya
                    istek["pot_al"] = True
                continue
            if istek.get("bayrak_test") is not None and not tehdit:
                adimlar_ = istek.pop("bayrak_test")
                bayrak_dene(adimlar_)
                continue
            if istek.get("beceri_goruntu") and not tehdit and kapat_s is not None:
                istek["beceri_goruntu"] = False
                print(f"{time.strftime('%H:%M:%S')}  beceri penceresi resmi "
                      + ("panel icin kaydedildi" if yetenek_penceresi_ac() else "alinamadi (pencere acilmadi)"))
                pencereleri_kapat()
                continue
            if beceri_gerek and not tehdit and ayar["beceri_puani_dagit"] and kapat_s is not None:
                beceri_gerek = False
                try:
                    beceri_puani_ver()
                except Exception:
                    import traceback
                    traceback.print_exc()
                continue

            # acik pencereleri kapat (tespiti bozuyorlar)
            if kapat_s is not None and time.time() - son_pencere > 15:
                son_pencere = time.time()
                acik = acik_pencereler(kare, kapat_s)
                if acik:
                    for px, py in acik:
                        tikla(px, py)
                        time.sleep(0.25)
                    pydirectinput.moveTo(ox + gen // 2, oy + int(yuk * 0.75))
                    continue

            # gorev parsomenleri: en az denenmisine tikla, acilan pencereyi Enter ile ilerlet
            if (not tehdit and ayar["gorev_parsomen"] and ayar["gorev_araligi_sn"]
                    and time.time() - son_gorev > ayar["gorev_araligi_sn"]):
                son_gorev = time.time()
                simgeler = gorev_simgeleri(kare)
                if simgeler:
                    gx, gy = min(simgeler, key=lambda p: (gorev_deneme.get(p[1] // 20, 0), p[1]))
                    gorev_deneme[gy // 20] = gorev_deneme.get(gy // 20, 0) + 1
                    gorev_sira += 1
                    taban = orta_parlaklik(kare)
                    tikla(gx, gy)
                    time.sleep(1.0)
                    gk = os.path.join(KLASOR, "goruntu", "gorev")
                    os.makedirs(gk, exist_ok=True)
                    adim = len(diyalog_ilerlet([], "gorev", taban))
                    if adim:
                        print(f"{time.strftime('%H:%M:%S')}  gorev parsomeni acildi: {adim} adim")
                    pydirectinput.moveTo(ox + gen // 2, oy + int(yuk * 0.75))
                    continue

            # NPC'ye gitmeyi isteyen gorevler (Biyolog, Ji-min vb.)
            if (not tehdit and (ayar["npc_gorevleri"] or ayar["av_gorevi"]) and kapat_s is not None
                    and time.time() - son_npc_gorev > (max(ayar["npc_gorev_araligi_sn"], ayar["gorev_av_okuma_sn"])
                                                   if not ayar["npc_gorevleri"] else ayar["npc_gorev_araligi_sn"])):
                son_npc_gorev = time.time()
                zaman_yaz("npc_gorev", son_npc_gorev)
                try:
                    if npc_gorevi_yap():
                        continue
                except Exception:
                    import traceback
                    traceback.print_exc()

            # beceri puani: sag altta "Becerileri Gelistir" simgesi gorununce dagit
            if statu_simge is not None and time.time() - son_beceri_simge > 30:
                son_beceri_simge = time.time()
                if simge_bul(kare[yuk - 200:, gen - 400:], statu_simge, 0.9) is not None:
                    beceri_gerek = True

            # statu puani: simge gorununce dagit
            if not tehdit and ayar["statu"] and statu_simge is not None and time.time() - son_statu > 20 and sakin_mi(kare):
                son_statu = time.time()
                if statu_gelistir(kare):
                    continue

            # envanterden kullanilanlar (hiz iksirleri, seviye sandigi): zamani gelenlere sag tikla
            # iksir: etkisi bitince (ogrenilen sure dolunca) icilir; sandik: yalniz 10, 20, 30... seviyede bir kez
            zamani = [e for e in envanter if time.time() >= e["sonraki"]
                      and (not e["sandik"] or (benim_sev and benim_sev % 10 == 0
                                               and durum_oku().get("sandik_sev") != benim_sev))]
            if zamani and (saldiri_altinda() or can < 0.8 or any(
                    math.hypot(t[0] - gen // 2, t[1] - yuk * 0.58) < 420 for t in kirmizi_etiketler(kare))):
                zamani = []                                   # savasta envantere dalma (yatiyordu): sakin ani bekle
            if zamani and not spotta and not tehdit:
                su_an[0] = "envanter (iksir/sandik)"
                k_env, acildi = kare, False
                if any(esya_bul(k_env, e["sablon"]) is None for e in zamani):
                    pydirectinput.press(ayar["envanter_tusu"])
                    acildi = True
                    time.sleep(0.4)
                    k_env = kare_al(h)
                for e in zamani:
                    yer = esya_bul(k_env, e["sablon"])
                    if yer is None:                     # envanterde yok: 10 dk sonra yeniden bak
                        e["sonraki"] = time.time() + 600
                        if e["sandik"]:
                            durum_yaz(sandik_sev=benim_sev)
                    if yer is not None:
                        pydirectinput.moveTo(ox + yer[0], oy + yer[1])
                        time.sleep(0.15)
                        pydirectinput.click(button="right")
                        time.sleep(0.35)
                        pydirectinput.moveTo(ox + gen // 2, oy + int(yuk * 0.75))
                        time.sleep(0.15)
                        k_son = kare_al(h)                  # adet rakami degisti mi (gercekten icildi mi)
                        a_, b_ = (kk[yer[1] + 2:yer[1] + 18, yer[0] - 4:yer[0] + 26].astype(int) for kk in (k_env, k_son))
                        fark_ = float(np.abs(a_ - b_).mean())
                        simdi_ = time.time()
                        if e["sandik"]:
                            durum_yaz(sandik_sev=benim_sev)
                            e["sonraki"] = simdi_ + 5
                            not_ = f"Lv {benim_sev} sandigi"
                        elif e["sabit"]:                      # sabit aralik: basildi, aralik kadar sonra yeniden
                            e["icildi"], e["sonraki"] = simdi_, (float("inf") if e["olunce"] else simdi_ + e["sure"])
                            d_ = durum_oku().get("iksir_icildi", {})
                            d_[e["ad"]] = simdi_
                            durum_yaz(iksir_icildi=d_)
                            not_ = ("kullanildi" if fark_ > 6 else "basildi (etki suruyor olabilir)") + f", sonraki {e['sure'] / 60:.0f} dk sonra"
                        elif fark_ > 6:                       # icildi
                            if e["ayni"] and e["icildi"]:      # once "hala etkin" dedi, simdi icildi: sure ogrenildi
                                e["sure"] = max(30.0, simdi_ - e["icildi"] - 5)
                                d_ = durum_oku().get("iksir_sure", {})
                                d_[e["ad"]] = round(e["sure"])
                                durum_yaz(iksir_sure=d_)
                            e["icildi"], e["ayni"], e["sonraki"] = simdi_, False, simdi_ + e["sure"]
                            e["bekle"] = 22
                            d_ = durum_oku().get("iksir_icildi", {})
                            d_[e["ad"]] = simdi_
                            durum_yaz(iksir_icildi=d_)
                            not_ = f"icildi, sonraki {e['sure'] / 60:.1f} dk sonra"
                        else:                                 # adet ayni: etkisi suruyor, 45 sn sonra yeniden
                            e["bekle"] = min(300, e.get("bekle", 22) * 2)   # 45, 90, 180, 300 sn: envanteri sik acma
                            e["ayni"], e["sonraki"] = True, simdi_ + e["bekle"]
                            not_ = "etkisi suruyor (adet ayni)"
                        print(f"{time.strftime('%H:%M:%S')}  envanter: {e['ad']}: {not_} (fark {fark_:.1f})")
                        k_env = k_son
                if acildi:
                    pydirectinput.press(ayar["envanter_tusu"])
                    time.sleep(0.4)
                pydirectinput.moveTo(ox + gen // 2, oy + int(yuk * 0.75))
                continue

            if ayar["beceri_tuslari"] and time.time() - son_beceri > ayar["beceri_araligi_sn"]:
                for t in ayar["beceri_tuslari"]:
                    pydirectinput.press(t)
                    time.sleep(0.5)
                son_beceri = time.time()

            tas = metin_taslari(kare, sablon) if ayar["mod"] in ("metin", "ikisi") else []
            if ayar["metin_kes"]:
                adaylar = beyaz_etiketler(kare)
                if adaylar and not tehdit and time.time() - son_metin_tarama > ayar["metin_tarama_sn"]:
                    son_metin_tarama = time.time()
                    yeni_tas = []
                    for t in adaylar:
                        x_, y_, w_, hh_ = t
                        yazi_ = " ".join(q["yazi"] for q in oku.oku(kare, kutu=(x_ - w_ // 2 - 60, y_ - hh_ - 6, x_ + w_ // 2 + 8, y_ + 6), olcek=4))
                        if any(oku.benzer(yazi_, w) for w in ayar["metin_kelimeleri"]):
                            yeni_tas.append(t)
                            if not metin_gorulen:
                                print(f"{time.strftime('%H:%M:%S')}  metin tasi goruldu: {yazi_}")
                                Image.fromarray(kare).save(os.path.join(KLASOR, "goruntu", "metin_goruldu.png"))
                    metin_gorulen = yeni_tas
                elif not adaylar:
                    metin_gorulen = []
                else:                                   # taramalar arasi: konumu guncelle
                    metin_gorulen = [min(adaylar, key=lambda q: abs(q[0] - t[0]) + abs(q[1] - t[1])) for t in metin_gorulen]
            if metin_gorulen:
                tas = tas + [t for t in metin_gorulen if t not in tas]
            yaratik = kirmizi_etiketler(kare) if ayar["mod"] in ("slot", "ikisi") else []
            karakter_ = (gen // 2, int(yuk * 0.58))
            saldiran = [t for t in yaratik
                        if math.hypot(t[0] - karakter_[0], t[1] - (karakter_[1] - 110)) < ayar["saldiran_yaricapi_piksel"]]
            # seviye: kendi seviyeni oku, fazla yuksekleri ele, kendi seviyen ve ustunu one al
            okunan = oyuncu_seviyesi(kare)                 # bastaki etiket: yalniz "degisti mi" ipucu
            if okunan:
                if okunan == sev_aday[0]:
                    sev_aday[1] += 1
                else:
                    sev_aday[0], sev_aday[1] = okunan, 1
            gecen_c = time.time() - son_c_seviye[0]
            if (gecen_c > ayar["seviye_kontrol_dk"] * 60
                    or (okunan and okunan != benim_sev and sev_aday[1] >= 5 and gecen_c > 600)):
                son_c_seviye[0] = time.time()
                zaman_yaz("c_seviye", son_c_seviye[0])
                okunan = seviye_karakterden()
                if okunan and okunan != benim_sev:
                    print(f"{time.strftime('%H:%M:%S')}  seviye: {okunan} (karakter penceresinden)")
                    if plan["sev"] != okunan:
                        plan["sev"], plan["p"] = okunan, plan_hesapla(bilgi, okunan)
                        print(f"{time.strftime('%H:%M:%S')}  plan: {plan['p']['yazi']}")
                    beceri_gerek = True
                    benim_sev = okunan
                    durum_yaz(son_seviye=okunan)
                continue
            karakter = (gen // 2, int(yuk * 0.58))
            ust = (benim_sev or ayar["en_fazla_yaratik_seviyesi"]) + (ayar["seviye_ust_fark"] if benim_sev else 0)
            if temkinde() and benim_sev:                       # art arda olum: bir sure yalniz kolay yaratik
                ust = min(ust, benim_sev + ayar["temkin_ust_fark"])
            sirali = []
            dusuk_var = 0
            tum_y = list(yaratik)

            def yog(t, tum_y=tum_y):
                return sum(1 for u in tum_y if math.hypot(t[0] - u[0], t[1] - u[1]) < ayar["slot_yaricapi_piksel"])

            for t in yaratik:
                sev = yaratik_seviyesi(kare, t)
                if sev is not None and (not benim_sev or abs(sev - benim_sev) <= 15):
                    sev_gorulen.append((time.time(), sev))
                    del sev_gorulen[:-80]
                uzak = (dunya_uzak(t[0], t[1] + 45, karakter[0], karakter[1], ayar["derinlik_ufuk"], ayar["derinlik_carpan"])
                        if ayar["derinlik_sirala"] else math.hypot(t[0] - karakter[0], t[1] - karakter[1]))
                if sev is None:
                    if 0 < seviye_hanesi(kare, t) <= len(str(ust)):
                        sirali.append(((0, int(uzak // ayar["yakinlik_halkasi_piksel"]), -yog(t), 0, uzak), t))  # okunamadi
                elif sev > ust:
                    continue                                # fazla guclu
                elif spotta or (benim_sev and sev >= benim_sev - ayar["seviye_alt_fark"]):
                    # seviyeme yakin (exp veren): once yakin halka, halka icinde yuksek seviye
                    sirali.append(((0, int(uzak // ayar["yakinlik_halkasi_piksel"]), -yog(t), -sev, uzak), t))
                elif ayar["dusuk_seviye_kesme"] and not alan_aktif() and can > 0.6 and time.time() > dusuk_izin[0]:
                    dusuk_var += 1                          # seviyeme gore cok dusuk (exp vermez): kesme
                else:
                    sirali.append(((1, int(uzak // ayar["yakinlik_halkasi_piksel"]), -yog(t), -sev, uzak), t))
            yaratik = [t for _, t in sorted(sirali, key=lambda s: s[0])]
            if atla:                                              # az once ulasilamayanlari 12 sn atla
                yaratik = [t for t in yaratik if not any(time.time() - z < (ayar['hizli_vazgec_atla_sn'] if ayar['hizli_vazgec'] else 12) and math.hypot(t[0] - ax, t[1] - ay) < 70
                                                         for z, ax, ay in atla)]
            yog_gorulen.append((time.time(), sum(1 for k_s, _ in sirali if k_s[0] == 0)))
            del yog_gorulen[:-300]
            # yalniz slot: birbirine yakin en az N yaratiktan olusan gruplarin uyeleri hedef alinir,
            # tek basina gezenlere gidilmez (uzun sure grup cikmazsa teklilere de izin verilir)
            if ayar["sadece_slot"] and bos_tur < ayar["tekli_bekleme_turu"]:
                tum = kirmizi_etiketler(kare)
                uye = set()
                for t in tum:
                    komsu = sum(1 for u in tum if math.hypot(t[0] - u[0], t[1] - u[1]) < ayar["slot_yaricapi_piksel"])
                    if komsu >= ayar["slot_en_az"]:
                        uye.add((int(t[0]), int(t[1])))
                dipte = {(int(t[0]), int(t[1])) for t in tum
                         if math.hypot(t[0] - karakter[0], t[1] - (karakter[1] - 110)) < ayar["saldiran_yaricapi_piksel"]}
                yaratik = [t for t in yaratik if (int(t[0]), int(t[1])) in uye or (int(t[0]), int(t[1])) in dipte]
                yaratik.sort(key=lambda t: 0 if (int(t[0]), int(t[1])) in dipte else 1)
            if time.time() < olum_sayac.get("dalma_yok_bitis", 0):    # art arda olum: kalabaliga dalma
                yaratik = [t for t in yaratik if yog(t) <= 2]
            # dibindeki (vuran) yaratiklar seviyesine bakilmadan en basa
            if ayar["dusuk_seviye_kesme"] and benim_sev and can > 0.6 and not saldiri_altinda():    # vurmayan dusuk seviyeliye oyalanma
                saldiran = [t for t in saldiran
                            if (yaratik_seviyesi(kare, t) or 99) >= benim_sev - ayar["seviye_alt_fark"]]
            saldiran.sort(key=lambda t: dunya_uzak(t[0], t[1] + 45, karakter[0], karakter[1], ayar["derinlik_ufuk"], ayar["derinlik_carpan"]))
            yaratik = saldiran + [t for t in yaratik if t not in saldiran]
            # gorevin istedigi yaratik ekrandaysa (adi okunur) slot sartina bakilmadan en basa
            aranan_adlar = (list(ayar["aranan_yaratiklar"]) + (aranan_durum if ayar["aranan_oncelik"] else [])
                            + (av_aranan if ayar["av_gorevi"] else []) + esya_hedef)
            if aranan_adlar and not tehdit and time.time() - son_aranan_tarama > ayar["aranan_tarama_sn"]:
                tum_k = kirmizi_etiketler(kare)
                if tum_k:
                    son_aranan_tarama = time.time()
                    bulunan = []
                    for q in oku.oku(kare, kutu=(gen // 2 - 650, 60, gen // 2 + 650, yuk - 180), olcek=2, renkli=True):
                        ad_q = re.sub(r"^(l[vu]\s*\d*\s*)", "", " ".join(oku.sade(q["yazi"]).split())).strip()
                        if len(ad_q.replace(" ", "")) >= 5:
                            ad_gorulen.append((time.time(), ad_q))
                            del ad_gorulen[:-60]
                        if not any(oku.benzer(q["yazi"], a_, 0.85) for a_ in aranan_adlar):
                            continue
                        if any(oku.benzer(q["yazi"], a_, 0.85) for a_ in av_aranan + esya_hedef):
                            son_av[0] = time.time()
                        t = min(tum_k, key=lambda t: abs(t[1] - t[3] / 2 - q["y"]) * 4 + abs(t[0] - q["x"]))
                        if abs(t[1] - t[3] / 2 - q["y"]) < 14 and q["x0"] - 20 < t[0] < q["x1"] + 20:
                            sev = yaratik_seviyesi(kare, t)
                            if (sev is None or sev <= ust) and t not in bulunan:
                                bulunan.append(t)
                        if time.time() - son_aranan_log > 60:
                            son_aranan_log = time.time()
                            print(f"{time.strftime('%H:%M:%S')}  aranan yaratik goruldu: {q['yazi']}")
                            Image.fromarray(kare).save(os.path.join(KLASOR, "goruntu", "aranan_goruldu.png"))
                    if bulunan:
                        bulunan.sort(key=lambda t: math.hypot(t[0] - karakter[0], t[1] - karakter[1]))
                        yaratik = bulunan + [t for t in yaratik if t not in bulunan]
            if ayar["sadece_hedefler"]:
                kendini_koru = [t for t in saldiran if can < 0.5 or saldiri_altinda()]
                yaratik = kendini_koru + [t for t in sadece_suz(kare, yaratik) if t not in kendini_koru]
            if tas:
                tas = sorted(tas, key=lambda t: math.hypot(t[0] - karakter[0], t[1] - karakter[1]))
            hedefler, sure = (tas, ayar["metin_vurus_suresi_sn"]) if tas else (yaratik, ayar["hedef_basi_ust_sure_sn"])
            dibimde_ = [t for t in kirmizi_etiketler(kare)                     # dibime gelen: filtre ne derse desin once o
                        if math.hypot(t[0] - karakter[0], t[1] + 45 - karakter[1]) < ayar["yakin_saldir_piksel"]]
            if (saldiri_altinda() or (can < ayar["savunma_can_esigi"] and saldiran)
                    or (ayar["yakin_saldir"] and dibimde_ and not tas)):  # vuruluyorum ya da dibimde: once yanimdakiler
                yakin_ = sorted((t for t in kirmizi_etiketler(kare)
                                 if math.hypot(t[0] - karakter[0], t[1] + 45 - karakter[1]) < ayar["savunma_yaricapi_piksel"]),
                                key=lambda t: math.hypot(t[0] - karakter[0], t[1] + 45 - karakter[1]))
                if yakin_:
                    if su_an[0] != "savunma":
                        print(f"{time.strftime('%H:%M:%S')}  hasar aliyorum - yanimdaki {len(yakin_)} yaratiga donuluyor")
                    su_an[0] = "savunma"
                    hedefler, sure = yakin_, ayar["hedef_basi_ust_sure_sn"]
                    pydirectinput.keyDown(ayar["saldiri_tusu"])       # tiklamadan once hemen vurmaya basla
                    if len(yakin_) >= 2 and ayar["saldiri_becerileri"]:
                        pydirectinput.press(ayar["saldiri_becerileri"][0]["tus"])   # cevreye vuran beceri (kilic cevirme)
                    time.sleep(0.25)
                    pydirectinput.keyUp(ayar["saldiri_tusu"])

            odak_d = list(ayar["sadece_hedefler"]) + esya_hedef + (av_aranan if ayar["av_gorevi"] else [])
            if (odak_d and not tehdit and not tas and not saldiran
                    and time.time() - son_av[0] > 240 and time.time() - son_av[1] > 240):
                son_av[1] = time.time()
                if any(any(oku.benzer(a_, o_, 0.85) for a_ in v_ for o_ in odak_d)
                       for v_ in durum_oku().get("bolge_ad", {}).values()):
                    print(f"{time.strftime('%H:%M:%S')}  av gorevi yaratigi 4 dk'dir gorulmedi - bilinen bolgesine gidiliyor")
                    try:
                        gezin()
                    except Exception:
                        import traceback
                        traceback.print_exc()
                    continue
            if not hedefler and saldiri_altinda():       # gorunen hedef yok ama vuruluyorum: yerinde vur, gitme
                su_an[0] = "vuruluyor - yerinde vuruyor"
                pydirectinput.keyDown(ayar["saldiri_tusu"])
                time.sleep(1.0)
                pydirectinput.keyUp(ayar["saldiri_tusu"])
                continue
            if not hedefler:
                bos_tur += 1
                if time.time() - son_gezin[0] < ayar["gezin_bekle_sn"]:    # yuruyus suruyor: bolme, hedef ara
                    su_an[0] = "yuruyor (hedef ariyor)"
                    time.sleep(0.25)
                    continue
                # cevrede yalniz dusuk seviyeli varsa ve 3 dk'da 3 kez yer degistirildiyse: bos durma, onlari da kes
                if dusuk_var >= 2:
                    dusuk_gezin[:] = [z for z in dusuk_gezin if time.time() - z < 180] + [time.time()]
                    if len(dusuk_gezin) >= 3 and time.time() > dusuk_izin[0]:
                        dusuk_izin[0] = time.time() + ayar["dusuk_izin_sn"]
                        dusuk_gezin.clear()
                        print(f"{time.strftime('%H:%M:%S')}  cevrede yalniz dusuk seviyeli var - {ayar['dusuk_izin_sn']} sn onlari da kesiyor (bos durmasin)")
                        continue
                # (toplama slot bitince yapildi; Z ayrica surekli basiliyor)
                # kamera surekli donerken bak (en cok ~2.5 sn); slot gorunurse hemen ona don.
                # 3 turda da uygun hedef cikmadiysa (ya da cevrede yalniz dusuk seviyeli varsa) beklemeden baska bolgeye
                if bos_tur < 3 and dusuk_var < 2 and etrafa_bak(ayar["etrafa_bakma_sn"]):
                    continue
                if (ayar.get("mini_harita_yuru", True) and not alan_aktif() and dusuk_var < 2
                        and alan.get("mini", 0) < 3):
                    alan["mini"] = alan.get("mini", 0) + 1
                    if mini_harita_yuru():
                        continue
                alan_bos_ = alan_aktif() and time.time() - son_savas[0] > ayar["alan_bos_sn"]   # 10 sn slot yok: alana don
                if alan["yerel"] < ayar["alan_kisa_yuruyus"] and dusuk_var < 2 and not alan_bos_:
                    alan["yerel"] += 1
                    alan_ici_yuru()
                    continue
                alan["yerel"] = 0
                print(f"{time.strftime('%H:%M:%S')}  alan: {ayar['alan_kisa_yuruyus']} kisa yuruyuste hedef yok - yeni alana")
                try:
                    gezin()
                except Exception:
                    import traceback
                    traceback.print_exc()
                continue
            bos_tur = 0
            alan["yerel"] = 0
            alan["mini"] = 0

            # 0) slota girmeden once: hava kilici / ofke sonmusse once yak (savas ortasinda yakilmaz)
            if (ayar["sureli_tuslar"] and can_orani(kare) >= ayar["guc_can_esigi"] and not saldiri_altinda()
                    and not tehdit and su_an[0] != "savunma"            # yaratik dibindeyken durup guclendirme yakma
                    and (not hedefler or math.hypot(hedefler[0][0] - karakter[0], hedefler[0][1] + 45 - karakter[1])
                         > ayar["guc_on_mesafe"])):                     # hedef yakinsa once vur, guclendirme sonra (sakinken)
                gecen_g = time.time() - guc["son"]
                if guc["hedef"] is None:
                    sonuk_ = gecen_g > min(t["aralik_sn"] for t in ayar["sureli_tuslar"])
                else:
                    sonuk_ = etki_sayisi(kare) < guc["hedef"] and gecen_g > ayar["guclendirme_en_az_aralik_sn"]   # beceri bekleme suresinde basip durmasin
                if sonuk_:
                    print(f"{time.strftime('%H:%M:%S')}  slottan once guclendirme")
                    guclendir()
                    kare = kare_al(h)

            # 1) ilk hedefi sec ve ilk vurusu yap
            su_an[0] = "hedefe gidiyor"
            if not sec(hedefler[0][0], hedefler[0][1]):
                # secilemeyen hedefte takilma: kamerayi cevir, olmazsa rastgele bir yere yuru
                secilemedi += 1
                pydirectinput.keyDown(ayar["kamera_tusu"])
                time.sleep(0.5)
                pydirectinput.keyUp(ayar["kamera_tusu"])
                if secilemedi >= 2:
                    aci = random.uniform(0, 2 * math.pi)
                    pydirectinput.moveTo(ox + karakter[0] + int(260 * math.cos(aci)),
                                         oy + karakter[1] + int(170 * math.sin(aci)))
                    pydirectinput.click()
                    time.sleep(1.5)
                    secilemedi = 0
                continue
            secilemedi = 0
            uzak_h = math.hypot(hedefler[0][0] - karakter[0], hedefler[0][1] + 45 - karakter[1])
            if (ayar["hamle_tusu"] and uzak_h > ayar["hamle_min_piksel"]
                    and time.time() - son_hamle[0] > ayar["hamle_aralik_sn"]):
                time.sleep(0.15)                                # hedef secildi, karakter donsun
                pydirectinput.press(ayar["hamle_tusu"])         # hedefe atil (yurumekten hizli)
                son_hamle[0] = time.time()
            kesilen += 1
            slot_bas = time.time()
            if not vurus_bekle(ayar["ilk_vurus_bekleme_sn"]):
                kacin(hedefler[0][0], hedefler[0][1], "ilk hedef, " + son_neden[0])   # nehir, ev vb. yuzunden ulasilamadi
                continue
            ulasilamayan = 0

            # 2) grup toplama: uzaktaki baska gruplardan birer yaratiga birer vurus at,
            #    pesine takilsinlar (can dusukse toplamayi birak)
            if not tas:
                for _ in range(max(0, ayar["toplanacak_grup"] - 1)):
                    k2 = kare_al(h)
                    if can_orani(k2) < ayar["toplama_can_siniri"] or not durum["calis"] or durum["duraklat"]:
                        break
                    uzaklar = yakindakiler(k2, ust, ayar["grup_ayrim_piksel"], ayar["toplama_en_uzak_piksel"])
                    if not uzaklar or not sec(uzaklar[0][0], uzaklar[0][1]):
                        break
                    if not vurus_bekle(ayar["ilk_vurus_bekleme_sn"]):
                        break                       # o gruba ulasilamadi: eldekilerle kesmeye gec

            # 3) kesme: etrafta yaratik kalmayana kadar saldiri tusu basili, ara vermeden vur
            bitis = time.time() + (ayar["metin_vurus_suresi_sn"] if tas else ayar["spot_ust_sure_sn"])
            bos, son_can, son_degisim = 0, 2.0, time.time()
            olduruldu, onceki_hc = 0, 0.0
            yaklasma = 0
            son_hasar = time.time()
            slot_atla = []                  # bu slotta ulasilamayan/vurulamayan yaratiklar (zaman, x, y): 20 sn secilmez
            yolo_deneme = [0]               # bu slotta sekil modeliyle (etiketsiz) yaratiga gidis sayisi
            pydirectinput.keyDown(ayar["saldiri_tusu"])
            saldiri_basili = True
            su_an[0] = "slot kesiyor"
            while time.time() < bitis and durum["calis"] and not durum["duraklat"]:
                uzaktan()
                if win32gui.GetForegroundWindow() != h:
                    break
                k2 = kare_al(h)
                if olum_denetle(k2):
                    break
                hc = hedef_cani(k2)
                if hc <= 0.03 and onceki_hc > 0.03:
                    olduruldu += 1                  # secili hedef oldu
                onceki_hc = hc
                if hc <= 0.03:                      # secili hedef yok: yakindaki siradakini sec
                    alt_s = (benim_sev - ayar["seviye_alt_fark"]
                             if ayar["dusuk_seviye_kesme"] and not alan_aktif() and benim_sev
                             and can_orani(k2) > 0.6 else None)
                    vuruluyor = saldiri_altinda()
                    if vuruluyor:                   # bana vuran var: seviye/ad filtresi yok, daha genis bak
                        alt_s = None
                    yakin = yakindakiler(k2, 9999, 0, ayar["spot_yaricapi_piksel"] + (160 if vuruluyor else 0), alt_s)
                    if ayar["sadece_hedefler"] and yakin and not vuruluyor:
                        yakin = sadece_suz(k2, yakin, hemen=True)
                    if yakin and not tas and oto["acik"] and saldiri_basili:
                        if oto["bas"] is None:
                            oto["bas"] = time.time()
                        if time.time() - oto["bas"] < 0.7:
                            time.sleep(0.05)
                            continue                # tus basili: oyun siradakini kendisi secerse hic durmadan vurur
                        oto["kacti"] += 1
                        if oto["kacti"] >= 3 and oto["tuttu"] == 0:
                            oto["acik"] = False
                            print(f"{time.strftime('%H:%M:%S')}  oto hedef: tus basiliyken yeni hedef secilmiyor - tiklamayla gecis")
                    oto["bas"] = None
                    if tas:
                        kx_, ky_ = gen // 2, int(yuk * 0.58)
                        yakin = [t for t in beyaz_etiketler(k2) if math.hypot(t[0] - kx_, t[1] - ky_) < 500] + yakin
                    if not yakin and not tas and bos >= 1:          # yakinda yaratik kaldikca slot bitmesin
                        # grup bitmedi: kamerayi kisa cevirip daha genis alanda (filtreye uyan) siradakini ara
                        if bos % 3 == 2:
                            birak()
                            pydirectinput.keyDown(ayar["kamera_tusu"])
                            time.sleep(0.3)
                            pydirectinput.keyUp(ayar["kamera_tusu"])
                        k2b = kare_al(h)
                        yakin = yakindakiler(k2b, 9999, 0, ayar["spot_yaricapi_piksel"] + 260, alt_s)
                        if ayar["sadece_hedefler"] and yakin and not vuruluyor:
                            yakin = sadece_suz(k2b, yakin, hemen=True)
                    if slot_atla and yakin:
                        slot_atla[:] = [a_ for a_ in slot_atla if time.time() - a_[0] < 20]
                        yakin = [t for t in yakin if not any(math.hypot(t[0] - a_[1], t[1] - a_[2]) < 70 for a_ in slot_atla)]
                    if not yakin and not tas and ayar.get("yolo_slot", True):
                        yb_ = yolo_yaratik_yakin(gen, yuk, ayar["spot_yaricapi_piksel"] + 160)
                        if yb_:                                  # atlanan noktadaysa ya da bu slotta 2 kez denendiyse tekrar gitme
                            yx_, yy_ = yb_[0], yb_[1] - ayar["etiket_alti_piksel"]
                            if yolo_deneme[0] < 2 and not any(math.hypot(yx_ - a_[1], yy_ - a_[2]) < 90 for a_ in slot_atla):
                                yolo_deneme[0] += 1
                                print(f"{time.strftime('%H:%M:%S')}  sekil: etiketsiz yaratik - vuruluyor")
                                yakin = [(yx_, yy_)]
                                slot_atla.append((time.time(), yx_, yy_))   # ulasilsa da ulasilamasa da ayni noktaya bir daha degil
                    if not yakin:
                        bos += 1
                        if vuruluyor and bos < 25:  # vuruluyor ama etiket gorunmuyor: yerinde vurmaya devam
                            if not saldiri_basili:
                                pydirectinput.keyDown(ayar["saldiri_tusu"])
                                saldiri_basili = True
                            time.sleep(0.12)
                            continue
                        if bos >= 2 and (tas or bos >= 6):
                            break                   # grup bitti (ya da ~2 sn aranip bulunamadi)
                        time.sleep(0.15)
                        continue
                    else:
                        bos = 0
                        birak()                     # yururken saldiri tusu basili olmasin
                        if not sec(yakin[0][0], yakin[0][1]) or not vurus_bekle(5):
                            yaklasma += 1
                            if yaklasma > (1 if ayar['hizli_vazgec'] else 2):
                                if (ayar.get("grupta_kal", True) and (len(yakin) > 1 or saldiri_altinda())
                                        and time.time() - son_hasar < ayar["grup_hasarsiz_sn"]):   # uzun suredir hic vuramiyorsa kal-ma
                                    slot_atla.append((time.time(), yakin[0][0], yakin[0][1]))
                                    yaklasma = 0
                                    print(f"{time.strftime('%H:%M:%S')}  slot ici: ulasilamayan yaratik atlandi - gruptakilere devam")
                                    pydirectinput.keyDown(ayar["saldiri_tusu"])
                                    saldiri_basili = True
                                    continue
                                kacin(yakin[0][0], yakin[0][1], "slot ici yeni hedef")
                                break
                            continue
                        yaklasma = 0
                        pydirectinput.keyDown(ayar["saldiri_tusu"])
                        saldiri_basili = True
                        son_can, son_degisim, son_hasar = 2.0, time.time(), time.time()
                else:
                    bos = 0
                    if oto["bas"] is not None:
                        oto["bas"] = None
                        oto["tuttu"] += 1
                        if oto["tuttu"] == 1:
                            print(f"{time.strftime('%H:%M:%S')}  oto hedef: tus basiliyken siradaki yaratik kendiliginden secildi")
                    if son_can > 1.5:
                        son_can = hc
                    elif hc < son_can - (0.005 if ayar.get("ince_vurus", True) else 0.01):   # 1 piksel dusus de vurus sayilir (guclu yaratik)
                        son_can, son_degisim = hc, time.time()
                        son_hasar = time.time()
                        yaklasma = 0
                        menzil_kaydet(k2, gen, yuk)             # vurus tuttu: bu uzaklik vurma mesafesinde
                    elif time.time() - son_degisim > vurus_sabri(k2, gen, yuk, son_degisim):   # vuramiyor: tusu birak, yaratiga yuru
                        yaklasma += 1
                        if yaklasma > (1 if ayar['hizli_vazgec'] else 2):   # uc (hizli: iki) denemede de vuramadi: ulasilamiyor
                            birak()
                            if ayar.get("grupta_kal", True):
                                nokta_ = govde_noktasi(k2, ayar["etiket_alti_piksel"])
                                diger_ = [t for t in yakindakiler(k2, 9999, 0, ayar["spot_yaricapi_piksel"] + 160, None)
                                          if not (nokta_ and abs(t[0] - nokta_[0]) < 60 and 0 < nokta_[1] - t[1] < 220)]
                                if (diger_ or saldiri_altinda()) and time.time() - son_hasar < ayar["grup_hasarsiz_sn"]:
                                    if nokta_:
                                        slot_atla.append((time.time(), nokta_[0], nokta_[1] - ayar["etiket_alti_piksel"]))
                                    yaklasma = 0
                                    print(f"{time.strftime('%H:%M:%S')}  slot ici: vurulamayan yaratik birakildi - gruptakilere devam")
                                    if diger_ and sec(diger_[0][0], diger_[0][1]):
                                        vurus_bekle(3)
                                    pydirectinput.keyDown(ayar["saldiri_tusu"])
                                    saldiri_basili = True
                                    son_can, son_degisim = 2.0, time.time()
                                    continue
                            kacin(gen // 2, int(yuk * 0.58) - 200, "vurulamayan hedef")
                            break
                        birak()
                        nokta = govde_noktasi(k2, ayar["etiket_alti_piksel"])
                        if nokta:
                            pydirectinput.moveTo(ox + nokta[0], oy + nokta[1])
                            time.sleep(0.05)
                            pydirectinput.click()
                            vurus_bekle(3)
                        pydirectinput.keyDown(ayar["saldiri_tusu"])
                        saldiri_basili = True
                        son_can, son_degisim = 2.0, time.time()
                if can_orani(k2) < ayar["can_esigi"]:
                    pydirectinput.press(ayar["can_potu_tusu"])
                guc_denetle(k2)
                time.sleep(0.0)
                if hc > 0.03 and time.time() - son_hasar < 1.5:
                    for bi, bc in enumerate(ayar["saldiri_becerileri"]):
                        if time.time() - son_saldiri_b.get(bi, 0) > bc["aralik_sn"]:
                            pydirectinput.press(bc["tus"])
                            son_saldiri_b[bi] = time.time()
                            time.sleep(0.12)
                            break
                time.sleep(0.08)
            birak()
            if (alan_aktif() and not saldiri_altinda()
                    and time.time() - son_gezin[0] > ayar["alan_donus_sn"]):
                alan_don[0] = True                          # slot bitince alana geri yuru (disariya kaymasin)
            son_savas[0] = time.time()
            if not tas:
                print(f"{time.strftime('%H:%M:%S')}  grup: {olduruldu} canavar kesildi")
                grup_sonu_guclendir()                           # hava kilici dolduysa sonraki gruba girmeden yak
                # grup bitti: can dolana kadar pot (vurulursa birak)
                bas_d = time.time()
                while time.time() - bas_d < 8 and durum["calis"] and not durum["duraklat"]:
                    can_d = can_orani(kare_al(h))
                    if can_d < 0.02 or can_d >= ayar["dolum_esigi"] or saldiri_altinda():
                        break
                    pydirectinput.press(ayar["can_potu_tusu"])
                    time.sleep(0.45)

            if tas:
                metin_gorulen = []
                son_metin_tarama = 0.0
            # 4) dusenleri topla
            time.sleep(0.1)
            topla()
            print(f"{time.strftime('%H:%M:%S')}  slot bitti ({time.time() - slot_bas:.0f} sn)")
            if kesilen % 20 == 0:
                print(f"{time.strftime('%H:%M:%S')}  kesilen hedef: {kesilen}  can %{can * 100:.0f}")
    finally:
        birak()
        uzaktan(kapaniyor=not yeniden_baslat[0])
        keyboard.unhook_all_hotkeys()
        print("Bot kapandi." if not yeniden_baslat[0] else "Bot yeni surumle yeniden aciliyor...")
    if yeniden_baslat[0]:
        sys.exit(3)


class _Kayit:
    """Ekrana yazilan her seyi bot.log dosyasina da yazar."""

    def __init__(self, asil):
        self.asil = asil
        self.dosya = open(os.path.join(KLASOR, "bot.log"), "a", encoding="utf-8", buffering=1)

    def write(self, s):
        self.asil.write(s)
        self.dosya.write(s)

    def flush(self):
        self.asil.flush()


def main():
    ayar = ayar_yukle()
    if "--dosya" not in sys.argv and "--kuru" not in sys.argv:
        sys.stdout = sys.stderr = _Kayit(sys.stdout)
        print(f"--- bot basladi {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    sablon_yol = os.path.join(KLASOR, "sablon", "metin.png")
    sablon = cv2.imread(sablon_yol, cv2.IMREAD_GRAYSCALE) if os.path.exists(sablon_yol) else None
    if "--dosya" in sys.argv or "--kuru" in sys.argv:
        if "--dosya" in sys.argv:
            kare = np.array(Image.open(sys.argv[sys.argv.index("--dosya") + 1]).convert("RGB"))
        else:
            kare = kare_al(pencere_bul(ayar["pencere_basligi"]))
        y, t, c = kirmizi_etiketler(kare), metin_taslari(kare, sablon), can_orani(kare)
        cikti = os.path.join(KLASOR, "goruntu", "tespit.png")
        ciz(kare, y, t, c, cikti)
        print(f"can %{c * 100:.0f} | yaratik etiketi {len(y)}: {y} | metin tasi {len(t)} | sablon {'var' if sablon is not None else 'YOK'}")
        return
    if ayar["mod"] in ("metin", "ikisi") and sablon is None:
        print("UYARI: sablon/metin.png yok; metin tasi taninamaz.")
    # tek kopya: ikinci bir bot ayni anda tuslara basarsa ikisi birbirini bozar
    import win32event, winerror, win32api
    global _TEK_KOPYA
    _TEK_KOPYA = win32event.CreateMutex(None, False, "MetinBotTekKopya")
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        print("Baska bir bot zaten calisiyor - bu kopya kapaniyor (iki bot ayni anda calismaz).")
        sys.exit(0)
    calistir(ayar, sablon)


if __name__ == "__main__":
    main()
