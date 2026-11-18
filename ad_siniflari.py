"""Oyundaki AD ETIKETLERINDEN sinif cikarir (model yok; saf renk + sekil kurali, yalniz numpy + cv2).
Ana Python (C:/Python314) ve yolo_env ikisinde de calisir.

ad_etiketleri(rgb) -> [{x0, y0, x1, y1, sinif, guven, aciklama}, ...]   (kutu: yazinin / cercevenin kendisi)
  sinif: yaratik, metin, npc, oyuncu, pazar, esya   (YOLO sinif no: SINIF_NO)
         kendim = kendi karakterimiz (SaMRicKeTs) -> birlestirici atlamali
         evcil  = 'Sahip - Kursun Asker' bicimli evcil hayvan adi (yesil; NPC degil, YOLO'ya girmemeli)
  guven: kuralin ne kadar kesin oldugu (0.6 = zayif yol: kenarda kesik Lv, kisa beyaz ad, konumla kendim...)

Deneme:  python ad_siniflari.py kare.jpg [cikti.jpg]   (cizim varsayilan: goruntu/ad_test/<ad>_ad.jpg)

OLCULEN kurallar (OpenCV HSV, H 0-179; ham kareler JPG, 1920x1111):
  Lv yazisi   : H 41-47 (%5-%95, 622 yaratik etiketi), S >= 92, yerel kontrast (V - 5x5 min) >= 89
  yaratik     : Lv + yalniz kirmizi ad. Kirmizi H 0-3/177, S >= 146, V >= 93 (bot.py kurali + koyu kirmizi)
  metin       : Lv + beyaz ad (S<=50, V>=165, ince cizgi) + 'Met' sablonu >= 0.55 (21 gercek tas adindan);
                beyaz ad kismi 72-84 px; uzun beyaz yazi = konusma balonu (atilir)
  npc         : Lv'siz yesil ad: PNG (104,196,79) H54; JPG H52-56; kontrast %5 = 93 (cimen medyani 56)
  evcil       : yesil ad + 'Sahip - Evcil' tiresi ya da 10-18 px sozcuk boslugu (normal bosluk 4-6 px)
  oyuncu      : Lv + kirmizi-disi renkler: ad sari (216,182,64) H23 (toprak H17'den ayrik), unvan mavi/mor
                (Kahraman H96, Arkadasca/Soylu/Iyi H120), Kotu Niyetli/Zalim kirmizi, Agresif turuncu
  kendim      : 'SaMRicKeTs' ad sablonu >= 0.55 (kendi adimiz 0.70-0.97, diger oyuncular <= 0.29);
                tutmazsa ekran ortasindaki Lv'li etiket (karakterin basi, y ~ %44)
  pazar       : koyu cerceve, 37-39 px yukseklik, kose suslari (cerceve cizgisi koseden 9-10 px iceride),
                yazi soluk gri-beyaz (p90 parlaklik medyani 200) kutunun orta bandinda
  esya        : ince koyu cerceve (kose susu yok), 18 px (tek satir) ya da 39 px (sari sahip adi + esya),
                yazi kutuyu dolduracak genislikte ve parlak beyaz (p90 >= 228, n=59)
  arayuz      : mini harita, alt cubuk, sohbet, sol ust etki simgeleri, sag etkinlik simgesi, Vote4Buff;
                acik pencereler (baslik cubugu + sol kenar cizgisi), hedef penceresi ve sistem duyurusu
                (yalniz gorunduklerinde) maskelenir.

DOGRULAMA (20 kare gozle, goruntu/ad_test/; kurallarin bir kismi bu karelere bakarken duzeltildi):
  yaratik 131 dogru / 0 yanlis / 21 kacan (9 ust uste binme, 8 arayuz altinda, 3 diyalog arkasinda, 1 cati)
  metin 1/1 (ayrica tum karelerde 22 'Lv+beyaz' adayi: 21 gercek tas, 1 konusma -> 21/21, 0 yanlis)
  npc 8 dogru / 1 yanlis sinif (NPC adi kendi etiketimizle cakisti -> evcil) | evcil 5 dogru, 1 kacan
  oyuncu 25 dogru / 0 yanlis / 8 kacan | kendim 14/16 (2 kacan: diyalog arkasi, NPC adiyla cakisma)
  pazar 12 dogru / 0 yanlis / 12 kacan (kalabalik pazarda ust uste binen tabelalar: ZAYIF)
  esya 11 dogru / 0 yanlis / 3 kacan (ayrica 50 karelik esya setinde 61/62 dogru)
"""
import os
import sys

import cv2
import numpy as np

SINIF_NO = {"yaratik": 0, "metin": 1, "npc": 2, "oyuncu": 3, "pazar": 4, "esya": 5}

# renk sinifi kodlari (piksel haritasi)
LV, YESIL, KIRMIZI, SARI, TURUNCU, MAVI, MOR, BEYAZ = 1, 2, 3, 4, 5, 6, 7, 8
RENK_ADI = {LV: "lv", YESIL: "yesil", KIRMIZI: "kirmizi", SARI: "sari", TURUNCU: "turuncu",
            MAVI: "mavi", MOR: "mor", BEYAZ: "beyaz"}


# 'Met' sozcuk basi (gri, 12x25): 'Lv NN ... Metini / Metin' adlarinin ortak parcasi. 20 gercek metin tasi
# adindan (Uzuntu / Savas / Siyah / Dovus Metini, ham kareler) hizalanip ortalandi. Birini-disarida-birak
# puanlari 0.54-0.95 (n=21); konusma balonu 0.44; diger Lv'li etiketlerde en yuksek 0.53 (n=72).
MET_SABLON = np.array([
    [85, 45, 36, 57, 87, 89, 87, 56, 36, 50, 85, 90, 88, 91, 92, 95, 97, 59, 61, 98, 95, 50, 73, 97, 96],
    [62, 107, 119, 91, 60, 82, 60, 94, 119, 104, 61, 83, 88, 90, 91, 92, 61, 95, 93, 58, 61, 108, 81, 71, 99],
    [31, 203, 251, 148, 24, 75, 20, 156, 251, 194, 27, 73, 78, 69, 75, 88, 23, 155, 148, 9, 38, 150, 85, 46, 74],
    [29, 207, 233, 143, 46, 72, 45, 149, 235, 196, 25, 68, 59, 44, 49, 75, 21, 156, 164, 44, 73, 59, 66, 66, 43],
    [29, 204, 125, 113, 165, 49, 173, 109, 133, 194, 21, 27, 133, 198, 164, 42, 7, 156, 230, 160, 50, 171, 95, 97, 204],
    [29, 203, 98, 107, 194, 39, 203, 97, 105, 194, 32, 138, 118, 85, 104, 150, 36, 157, 185, 68, 28, 203, 99, 105, 214],
    [29, 205, 95, 57, 131, 124, 129, 52, 108, 193, 39, 204, 171, 119, 150, 224, 51, 157, 149, 4, 22, 203, 99, 105, 195],
    [30, 203, 98, 2, 60, 213, 50, 2, 106, 193, 40, 205, 209, 182, 183, 168, 40, 157, 150, 4, 22, 203, 99, 105, 194],
    [29, 203, 96, 4, 57, 187, 51, 4, 107, 194, 36, 176, 118, 52, 50, 47, 12, 135, 145, 29, 24, 202, 100, 106, 195],
    [29, 196, 95, 30, 65, 51, 61, 29, 103, 187, 25, 40, 139, 198, 199, 183, 43, 33, 109, 152, 40, 193, 97, 101, 187],
    [61, 78, 66, 70, 79, 59, 80, 64, 67, 76, 55, 55, 75, 86, 86, 83, 65, 60, 71, 79, 67, 82, 68, 70, 80],
    [83, 47, 69, 91, 90, 86, 87, 87, 64, 48, 80, 85, 54, 35, 34, 44, 85, 94, 71, 53, 88, 54, 77, 74, 53],
], np.float32)
MET_ESIK = 0.55

# Kendi adimiz 'SaMRicKeTs' (gri, 14x70; sari ad). 6 temiz kendi etiketinden hizalanip ortalandi.
# Olcum (23 kare): kendi adimiz 0.70-0.97, diger oyuncu etiketleri <= 0.29.
AD_SABLON = np.array([
    [104, 103, 92, 91, 94, 92, 92, 103, 105, 106, 102, 99, 92, 92, 86, 77, 79, 96, 91, 88, 94, 84, 82, 84, 80, 71, 68, 68, 80, 89, 90, 87, 75, 84, 90, 86, 84, 85, 83, 84, 85, 82, 89, 89, 86, 81, 69, 77, 81, 88, 96, 96, 94, 84, 78, 66, 70, 74, 77, 72, 66, 72, 76, 80, 85, 84, 76, 71, 70, 67],
    [104, 102, 49, 38, 36, 41, 37, 84, 98, 98, 104, 100, 92, 85, 59, 30, 34, 78, 87, 80, 71, 35, 33, 60, 59, 34, 32, 32, 60, 79, 86, 81, 44, 63, 88, 80, 74, 74, 80, 84, 69, 39, 75, 84, 78, 65, 31, 64, 78, 84, 92, 93, 85, 79, 56, 30, 32, 34, 32, 32, 38, 70, 73, 75, 76, 76, 73, 76, 73, 72],
    [93, 42, 118, 145, 146, 144, 148, 65, 74, 103, 97, 97, 84, 50, 71, 146, 145, 58, 58, 62, 51, 140, 146, 82, 70, 146, 146, 144, 82, 48, 68, 35, 115, 85, 52, 81, 80, 83, 84, 65, 48, 141, 62, 59, 60, 44, 138, 58, 61, 86, 89, 91, 86, 47, 68, 146, 144, 146, 146, 146, 130, 34, 67, 76, 76, 74, 73, 76, 75, 76],
    [61, 102, 112, 110, 108, 108, 104, 43, 74, 78, 57, 52, 78, 30, 84, 210, 206, 44, 49, 48, 41, 201, 211, 88, 83, 194, 114, 108, 99, 86, 36, 38, 96, 61, 53, 76, 47, 49, 48, 26, 37, 196, 47, 31, 60, 108, 105, 49, 71, 71, 48, 47, 75, 56, 71, 108, 110, 184, 155, 107, 92, 38, 48, 42, 41, 44, 73, 77, 75, 74],
    [43, 198, 46, 8, 8, 10, 26, 78, 80, 64, 66, 71, 72, 26, 82, 203, 145, 77, 66, 56, 84, 146, 197, 87, 82, 172, 18, 11, 123, 125, 17, 52, 60, 62, 57, 56, 64, 66, 67, 44, 40, 198, 46, 40, 100, 122, 34, 70, 71, 64, 66, 69, 62, 75, 60, 23, 13, 166, 91, 14, 34, 48, 59, 67, 66, 69, 56, 73, 78, 78],
    [41, 168, 62, 38, 37, 46, 68, 86, 48, 75, 161, 159, 70, 21, 83, 174, 31, 155, 89, 80, 164, 32, 167, 88, 80, 181, 44, 38, 120, 112, 14, 16, 154, 87, 21, 64, 158, 160, 161, 99, 40, 196, 74, 107, 110, 35, 69, 72, 53, 85, 161, 157, 68, 59, 73, 63, 10, 164, 87, 32, 67, 18, 151, 176, 164, 137, 26, 66, 77, 73],
    [56, 42, 133, 162, 162, 138, 44, 72, 62, 56, 52, 52, 144, 74, 83, 171, 19, 157, 88, 86, 159, 18, 167, 88, 83, 197, 165, 172, 97, 44, 51, 10, 165, 88, 67, 154, 44, 43, 43, 24, 40, 198, 172, 101, 54, 68, 80, 32, 104, 132, 56, 52, 142, 87, 41, 66, 12, 163, 90, 33, 64, 14, 155, 114, 48, 40, 61, 74, 72, 80],
    [81, 56, 66, 66, 68, 79, 143, 61, 38, 73, 146, 148, 201, 87, 82, 172, 17, 57, 108, 117, 56, 12, 167, 86, 84, 186, 77, 178, 88, 33, 65, 12, 165, 91, 80, 171, 15, 40, 52, 33, 40, 202, 100, 105, 107, 42, 78, 19, 123, 183, 142, 150, 199, 87, 36, 69, 10, 164, 89, 31, 70, 52, 66, 107, 91, 17, 76, 77, 74, 78],
    [92, 57, 10, 5, 6, 42, 200, 46, 57, 112, 107, 110, 190, 82, 86, 170, 13, 5, 126, 128, 4, 10, 168, 89, 80, 171, 19, 88, 98, 84, 37, 10, 166, 87, 82, 171, 17, 36, 40, 24, 38, 195, 50, 67, 99, 98, 50, 8, 124, 174, 110, 111, 107, 64, 59, 71, 11, 164, 88, 33, 80, 67, 16, 65, 103, 98, 49, 70, 78, 73],
    [66, 65, 67, 67, 66, 85, 142, 41, 97, 109, 71, 75, 180, 88, 82, 170, 12, 15, 96, 92, 16, 11, 166, 87, 82, 171, 13, 21, 97, 111, 56, 12, 168, 89, 60, 128, 67, 66, 67, 42, 40, 198, 48, 18, 72, 127, 69, 20, 86, 114, 68, 68, 71, 64, 67, 62, 11, 163, 90, 29, 77, 50, 58, 69, 118, 173, 19, 63, 79, 80],
    [51, 156, 160, 162, 161, 139, 31, 64, 43, 76, 162, 165, 177, 75, 76, 144, 16, 42, 37, 34, 40, 17, 146, 74, 76, 146, 21, 58, 45, 76, 134, 25, 143, 77, 21, 52, 156, 162, 161, 106, 43, 166, 47, 48, 54, 52, 151, 44, 24, 76, 165, 162, 162, 82, 46, 70, 20, 143, 78, 34, 56, 23, 129, 162, 169, 148, 23, 62, 76, 77],
    [55, 41, 43, 41, 42, 42, 69, 78, 62, 52, 42, 41, 41, 45, 46, 39, 53, 62, 58, 56, 61, 56, 45, 37, 41, 36, 46, 71, 66, 59, 42, 58, 45, 45, 57, 60, 44, 45, 44, 46, 63, 42, 60, 80, 76, 63, 44, 59, 66, 58, 40, 41, 43, 56, 78, 82, 70, 49, 46, 64, 69, 63, 49, 42, 42, 43, 54, 83, 81, 78],
    [72, 47, 48, 51, 49, 56, 80, 84, 83, 65, 50, 51, 49, 58, 53, 42, 59, 61, 63, 61, 63, 59, 38, 38, 38, 41, 50, 57, 62, 57, 54, 66, 48, 53, 73, 72, 55, 56, 57, 72, 75, 59, 78, 86, 88, 81, 58, 78, 77, 62, 53, 54, 52, 78, 87, 86, 82, 57, 68, 74, 76, 74, 50, 48, 55, 54, 74, 84, 86, 83],
    [74, 78, 83, 82, 81, 80, 77, 72, 72, 80, 76, 82, 74, 63, 56, 56, 54, 56, 52, 52, 53, 44, 40, 37, 38, 40, 43, 38, 40, 50, 62, 61, 66, 70, 76, 86, 86, 82, 87, 88, 88, 90, 96, 93, 96, 94, 90, 78, 72, 71, 72, 78, 84, 87, 91, 87, 87, 82, 78, 79, 84, 75, 79, 82, 79, 76, 82, 86, 82, 79],
], np.float32)
AD_ESIK = 0.55


# ---------------------------------------------------------------- arayuz
def arayuz_maskesi(yuk, gen):
    """bot.py arayuz_maskesi + ek arayuz bolgeleri: True = yok say."""
    m = np.zeros((yuk, gen), bool)
    m[:210, gen - 190:] = True              # mini harita (+ 'Monastry, CH1' yazisi)
    m[yuk - 55:, :] = True                  # alt cubuk
    m[yuk - 135:, 580:1340] = True          # sohbet satirlari
    m[:50, :260] = True                     # sol ust etki simgeleri
    m[225:360, gen - 235:] = True           # sagdaki etkinlik simgesi + 'Bitis: ... Sonraki Etkinlik'
    m[yuk - 200:yuk - 110, 192:302] = True  # sol alt Vote4Buff simgesi (turuncu parsomen + yazi)
    return m


def pencere_maskesi(rgb):
    """Acik oyun pencereleri (envanter, harita, karakter, arkadaslar...): True = yok say.
    Olcum: baslik cubugu (60-110, 18-48, 6-14) -> R/G 2.3-3.3, G/B ~3 (kirmizi adda G~B), 18-20 px yuksek;
    pencerenin alt ucu sol kenardaki dikey koyu cizgiden bulunur."""
    yuk, gen = rgb.shape[:2]
    r, g, b = [rgb[..., i].astype(np.int16) for i in range(3)]
    ham = ((r >= 55) & (r <= 150) & (r * 10 > 18 * g) & (g * 10 >= 18 * b) & (g >= 12)).astype(np.uint8)
    baslik = cv2.morphologyEx(ham, cv2.MORPH_CLOSE, np.ones((5, 15), np.uint8))
    n, _, ist, _ = cv2.connectedComponentsWithStats(baslik, 8)
    koyu = rgb.max(axis=2) < 60
    m = np.zeros((yuk, gen), bool)
    for i in range(1, n):
        x, y, w, h, a = ist[i]
        # olcum (8 gercek cubuk / ust uste 2 kirmizi yaratik adi): kapali doluluk >= 0.84 / 0.58,
        # ham doluluk >= 0.59 / 0.11, sol kenar dikey koyu cizgi >= 381 / 38 px
        if w < 120 or not 16 <= h <= 32 or a / (w * h) < 0.75 or ham[y:y + h, x:x + w].mean() < 0.45:
            continue
        en = 0
        for cx in range(max(0, x - 100), min(gen, x + 6)):   # karakter penceresinde cubuk portrenin saginda
            kol = koyu[y:, cx]
            son, bos = 0, 0
            for j in range(len(kol)):
                if kol[j]:
                    son, bos = j, 0
                else:
                    bos += 1
                    if bos > 15:
                        break
            en = max(en, son)
        if en < 150:
            continue
        m[max(0, y - 8):y + en + 10, max(0, x - 100):x + w + 45] = True
    return m


def duyuru_maskesi(rgb):
    """Ust ortadaki sistem duyurusu kutusu: yalniz gorundugunde maskelenir.
    Olcum (5 karede sabit yer): y 88-96 koyu bant (max<50 orani >= 0.5), y 98-105 beyaz yazi, y 106-111 koyu bant;
    kutu ekrana ortali. Koyu kaya / golgede bantlar ve yazi birlikte olusmaz."""
    yuk, gen = rgb.shape[:2]
    m = np.zeros((yuk, gen), bool)
    o = gen // 2
    mx = rgb[80:120].max(axis=2)
    ust = (mx[8:16, o - 150:o + 150] < 50).mean()
    alt = (mx[26:31, o - 150:o + 150] < 50).mean()
    yazi = (rgb[98:106, o - 150:o + 150].min(axis=2) > 170).sum()
    if ust < 0.45 or alt < 0.35 or yazi < 30:
        return m
    sut = (mx[8:16] < 75).mean(axis=0) >= 0.5
    sol, bos = o, 0
    while sol > 0 and bos < 15:
        sol -= 1
        bos = 0 if sut[sol] else bos + 1
    sag, bos = o, 0
    while sag < gen - 1 and bos < 15:
        sag += 1
        bos = 0 if sut[sag] else bos + 1
    m[80:120, max(0, sol - 10):sag + 10] = True
    return m


# ---------------------------------------------------------------- renk haritasi
def renk_haritasi(rgb):
    """Her piksele yazi rengi sinifi (0 = yazi degil). Olculen esiklerle."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    # yerel kontrast: yazinin koyu golgesi/cercevesi var; cimen dokusunda yok (olcum: Lv %5 = 89, cimen %50 = 50)
    kon = cv2.subtract(V, cv2.erode(V, np.ones((5, 5), np.uint8)))
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros(H.shape, np.uint8)
    # oncelik sirasi: sonra yazilan ustune yazar
    # beyaz yazi: ince cizgi (1-2 px) ve iki yaninda koyu golge; parlak gok / duvarin koyu yazi kenarindaki
    # pikselleri yalniz bir yanda koyu oldugu icin elenir
    V16 = V.astype(np.int16)

    def iki_yan(eksen):
        a = np.minimum(np.roll(V16, 1, eksen), np.roll(V16, 2, eksen))
        b = np.minimum(np.roll(V16, -1, eksen), np.roll(V16, -2, eksen))
        return (V16 - a >= 45) & (V16 - b >= 45)
    ince = iki_yan(1) | iki_yan(0)
    h[(S <= 50) & (V >= 165) & (kon >= 60) & ince] = BEYAZ
    h[(H >= 140) & (H <= 171) & (S >= 50) & (V >= 110) & (kon >= 50)] = MOR
    h[(H >= 85) & (H <= 139) & (S >= 60) & (V >= 110) & (kon >= 50)] = MAVI
    # sari ad: toprak zemin H 14-19 (medyan 17), ad H medyan 23; kontrast ad %25 = 125, toprak %95 = 80
    h[(H >= 20) & (H <= 34) & (S >= 60) & (V >= 140) & (kon >= 90)] = SARI
    h[(H >= 8) & (H <= 13) & (S >= 120) & (V >= 140) & (kon >= 60)] = TURUNCU
    # yesil NPC adi kontrast %5 = 93 (10 etiket), cimen medyan 56; Lv %5 = 89 (622 etiket)
    h[(H >= 50) & (H <= 66) & (S >= 70) & (V >= 105) & (kon >= 85)] = YESIL
    h[(H >= 38) & (H <= 49) & (S >= 80) & (V >= 105) & (kon >= 80)] = LV
    kir = (r > 120) & (cv2.subtract(r, g) > 85) & (cv2.subtract(r, b) > 75) & (g < 90)   # bot.py kurali
    # + olculen koyu kirmizi (yaratik adi %5: V 93, S 146; JPG'de cimen ustunde bot kurali harf atliyor)
    kir |= ((H <= 5) | (H >= 173)) & (S >= 140) & (V >= 85) & (kon >= 40)
    h[kir] = KIRMIZI
    # tek basina duran 1-2 piksellik gurultuyu at (harf cizgileri en az 3-4 piksel bitisik)
    n, lab, ist, _ = cv2.connectedComponentsWithStats((h > 0).astype(np.uint8), 8)
    kucuk = ist[:, cv2.CC_STAT_AREA] <= 2
    kucuk[0] = False
    h[kucuk[lab]] = 0
    return h


# ---------------------------------------------------------------- kutular (pazar / esya)
def _ust_cizgiler(yatay):
    """Yatay koyu cizgi bilesenlerinden ust cerceve adaylari (x, y, w). Kalin / baska koyu seye
    yapisik bilesenlerde her satirin en uzun kosusu ayri aday olur."""
    n, _, ist, _ = cv2.connectedComponentsWithStats(yatay, 8)
    aday = []
    for i in range(1, n):
        x, y, w, hh, _ = ist[i]
        # koyu zemin onunde yari saydam tabela: ic koyu kosular ust cizgiyi alt cizgiye / zemine baglar,
        # bilesen 20 satirdan uzun olur (olcum 121949 'ucuz bklar': 306-344. satirlar tek bilesen).
        # Bunlar da satir satir taranir (eskiden hh > 20 tumden atiliyordu).
        if w < 16 or hh > 200:
            continue
        if hh <= 3 and w <= 420:
            aday.append((x, y, w))
            continue
        onceki = None
        for r in range(y, y + hh):
            satir = np.concatenate([[0], yatay[r, x:x + w], [0]]).astype(np.int8)
            fark = np.diff(satir)
            bas_, son_ = np.where(fark == 1)[0], np.where(fark == -1)[0]
            if not len(bas_):
                continue
            j = int(np.argmax(son_ - bas_))
            a, b = int(bas_[j]), int(son_[j])
            if 16 <= b - a <= 420 and not (onceki and abs(onceki[0] - a) < 4 and abs(onceki[1] - b) < 4):
                aday.append((x + a, r, b - a))
            onceki = (a, b)
    return aday


def kutular(rgb, maske):
    """Koyu cerceveli kutular: pazar tabelasi (kose suslu, 39 px) ve yerdeki esya ad kutusu.
    Donus: [(x0, y0, x1, y1, sinif, guven, aciklama)]"""
    yuk, gen = rgb.shape[:2]
    mx = rgb.max(axis=2)
    koyu = (mx < 45).astype(np.uint8)
    yatay = cv2.morphologyEx(koyu, cv2.MORPH_OPEN, np.ones((1, 16), np.uint8))
    yatay[maske] = 0
    # cerceve dogrulamasi icin hosgorulu koyu: JPEG cizgiyi acar / 1 satir kaydirir
    koyu50 = (mx < 50).astype(np.uint8)
    koyu50d = cv2.dilate(koyu50, np.ones((3, 1), np.uint8))
    # hizli aralik ortalamalari icin birikimli toplamlar (sol/ust sifir dolgulu)
    yat_cs = np.zeros((yuk, gen + 1), np.int32)
    yat_cs[:, 1:] = np.cumsum(koyu50d, axis=1)
    k50_cs = np.zeros((yuk, gen + 1), np.int32)
    k50_cs[:, 1:] = np.cumsum(koyu50, axis=1)
    dik_cs = np.zeros((yuk + 1, gen), np.int32)
    dik_cs[1:] = np.cumsum(koyu50, axis=0)
    parlak = rgb.min(axis=2) > 140                                          # beyaz/gri yazi
    sari = (rgb[..., 0] > 170) & (rgb[..., 1] > 130) & (rgb[..., 2] < 120)  # sahip adi
    yazi_px = parlak | sari
    sonuc = []
    for x, y, w in _ust_cizgiler(yatay):
        if y < 5:
            continue
        for dy in (16, 17, 18, 19, 35, 36, 37, 38, 39):    # olculen: esya 17 (tek satir), pazar/esya 37-38
            y2 = y + dy
            if y2 + 6 >= yuk:
                break
            if (yat_cs[y2, x + w] - yat_cs[y2, x]) / w < 0.75:
                continue
            ic0, ic1 = y + 3, y2 - 2
            # dikey kenar yalniz orta satirlarda aranir: pazarda kose suslari ust/alt 9 satiri kaplar
            k0, k1 = (y + 10, y2 - 9) if dy >= 33 else (ic0, ic1)
            sa, sb = max(0, x - 15), min(gen, x + w + 14)
            sutun_d = np.zeros(gen)
            sutun_d[sa:sb] = (dik_cs[k1, sa:sb] - dik_cs[k0, sa:sb]) / (k1 - k0)

            # sol / sag dikey kenar: esyada cizginin ucunda, pazarda kose susu yuzunden ~9-10 px disarida
            def kenar(aralik):
                en, en_x = 0.0, None
                for cx in aralik:
                    if 0 <= cx < gen and sutun_d[cx] > en + 0.02:
                        en, en_x = sutun_d[cx], cx
                return en, en_x
            sol_d, sol_x = kenar(range(x + 3, x - 15, -1))
            sag_d, sag_x = kenar(range(x + w - 4, x + w + 14))
            if sol_d < 0.75 or sag_d < 0.75 or sag_x - sol_x < 24 or sol_x < 5 or sag_x + 5 >= gen:
                continue
            ic = yazi_px[ic0:ic1, sol_x + 2:sag_x - 1]
            ickoyu = koyu[ic0:ic1, sol_x + 3:sag_x - 2].mean()
            if ic.sum() < 8 or ic.mean() > 0.45 or ickoyu > 0.6:
                continue
            # dis halka (cercevenin 3-4 px disi) zemin olmali; tooltip / envanter icinde her yer koyu
            # (olcum: gercek pazar 0.00-0.53, tooltip/envanter 0.44-0.94)
            ww = sag_x - sol_x + 1
            dis = sum(k50_cs[yy, sag_x + 1] - k50_cs[yy, sol_x] for yy in (y - 3, y - 4, y2 + 4, y2 + 5)) / (4 * ww)
            dis_d = sum(dik_cs[y2 + 1, xx] - dik_cs[y, xx] for xx in (sol_x - 3, sol_x - 4, sag_x + 3, sag_x + 4)) / (4 * (dy + 1))
            if (4 * ww * dis + 4 * (dy + 1) * dis_d) / (4 * ww + 4 * (dy + 1)) > 0.6:
                continue
            satir_say = (ic.sum(axis=1) >= 2)
            satir = np.where(satir_say)[0]
            sutun = np.where(ic.sum(axis=0) > 0)[0]
            if not len(satir):
                continue
            kaplama = (sutun[-1] - sutun[0] + 1) / ic.shape[1]
            bantlar = _bantlar(satir_say)
            ofs_sol, ofs_sag = x - sol_x, sag_x - (x + w - 1)
            if dy >= 35 and ofs_sol >= 5 and ofs_sag >= 5:
                # pazar: tek satir yazi kutunun ortasinda (olcum: ust kenardan 13-25. satirlar)
                orta = satir[len(satir) // 2] + 3
                if not 10 <= orta <= 28 or kaplama < 0.3:
                    continue
                # parlak piksellerin >= %80'i orta bantta (kutu ustunden 11-28. satir); yaprak arasi gok her yere dagilir
                sat_top = ic.sum(axis=1)
                if sat_top[8:26].sum() < 0.8 * sat_top.sum():
                    continue
                sonuc.append((sol_x, y - 1, sag_x, y2 + 1, "pazar", 0.85, f"kose suslu {dy + 1}px"))
                break
            if ofs_sol <= 3 and ofs_sag <= 3:
                if kaplama < 0.6:                           # esya kutusu yaziya gore boyutlanir (olcum >= 0.93)
                    continue
                # esya yazisi parlak beyaz (p90 >= 228, n=59); ust uste binmis pazar tabelasi yazisi soluk (<= 198, n=7)
                bz = ic & (rgb[ic0:ic1, sol_x + 2:sag_x - 1].min(axis=2) > 140)
                if bz.sum() >= 5 and np.percentile(mx[ic0:ic1, sol_x + 2:sag_x - 1][bz], 90) < 215:
                    continue
                # yazi satiri yapisi: tek satirda 1 bant (6-13 satir) ortada; iki satirda ust ve alt yarida birer bant
                iyi = [b_ for b_ in bantlar if 5 <= b_[1] - b_[0] <= 14]
                if dy < 35:
                    if len(iyi) != 1 or abs((iyi[0][0] + iyi[0][1]) / 2 - ic.shape[0] / 2) > 4:
                        continue
                elif len(iyi) != 2 or iyi[0][1] > ic.shape[0] / 2 + 2 or iyi[1][0] < ic.shape[0] / 2 - 2:
                    continue
                sar = sari[ic0:ic1, sol_x + 2:sag_x - 1].sum()
                sonuc.append((sol_x, y, sag_x, y2 + 1, "esya", 0.8,
                              ("iki satir" if dy >= 33 else "tek satir") + (" sahipli" if sar >= 8 else "")))
                break
    # ayni kutu iki kez (ust cizgi parcalari) -> tekille
    tek = []
    for k in sorted(sonuc, key=lambda k: -(k[2] - k[0]) * (k[3] - k[1])):
        if not any(_ortusme(k, t) > 0.5 for t in tek):
            tek.append(k)
    return tek


def _bantlar(satir_var):
    """Ardisik dolu satir bantlari [(bas, son)]; 1 satirlik bosluk bandi bolmez."""
    bant, bas, bos = [], None, 0
    for i, d in enumerate(list(satir_var) + [False, False]):
        if d:
            if bas is None:
                bas = i
            bos = 0
        elif bas is not None:
            bos += 1
            if bos >= 2:
                bant.append((bas, i - 1))
                bas, bos = None, 0
    return bant


def _ortusme(a, b):
    """Kucuk kutunun alaninin ne kadari digerinin icinde."""
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    kucuk = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return ix * iy / max(1, kucuk)


# ---------------------------------------------------------------- yazi satirlari
def _seritler(h, x0, y0, x1, y1):
    """Bilesen icinde yazi olan satir bantlari (ust uste binmis etiketleri ayirir)."""
    sat = (h[y0:y1, x0:x1] > 0).sum(axis=1)
    bantlar, bas, bos = [], None, 0
    for i, s in enumerate(list(sat) + [0, 0]):
        if s > 1:
            if bas is None:
                bas = i
            bos = 0
        elif bas is not None:
            bos += 1
            if bos >= 2 or i >= len(sat):
                bantlar.append((y0 + bas, y0 + i - bos + 1))
                bas, bos = None, 0
    return bantlar


def _kosular(say, x0):
    """Sutun basina renk sayimlarindan (8, w) renk parcalari: [(renk, xa, xb, piksel)]"""
    dolu = say.sum(axis=0)
    baskin = np.where(dolu > 0, say.argmax(axis=0) + 1, 0)
    kosu = []
    for j, c in enumerate(baskin):
        if c == 0:
            continue
        if kosu and kosu[-1][0] == c and j - kosu[-1][2] <= 12:
            kosu[-1][2] = j
            kosu[-1][3] += int(dolu[j])
        else:
            kosu.append([int(c), j, j, int(dolu[j])])
    temiz = []
    for k in kosu:                                   # cok dar gurultu parcalari (JPEG hale rengi) atilir
        if k[2] - k[1] < 2 and k[3] < 6:
            continue
        if temiz and temiz[-1][0] == k[0] and k[1] - temiz[-1][2] <= 12:
            temiz[-1][2], temiz[-1][3] = k[2], temiz[-1][3] + k[3]
        else:
            temiz.append(k)
    return [(c, x0 + a, x0 + bb + 1, p) for c, a, bb, p in temiz]


def _say(b):
    return np.stack([(b == c).sum(axis=0) for c in range(1, 9)])


def lv_capalari(h, maske=None):
    """'Lv NN' yazilari (her yaratik / metin / oyuncu etiketinin basi): [(x0, y0, x1, y1)]"""
    m = (h == LV).astype(np.uint8)
    k = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((1, 13), np.uint8))   # 'Lv' ile rakam arasi ~9 px
    n, _, ist, _ = cv2.connectedComponentsWithStats(k, 8)
    sonuc = []
    for i in range(1, n):
        x, y, w, hh, _ = ist[i]
        sut = np.where(m[y:y + hh, x:x + w].any(axis=0))[0]      # kapama kenarda sutun doldurabilir: kirp
        if not len(sut):
            continue
        x, w = x + int(sut[0]), int(sut[-1] - sut[0] + 1)
        # rakamlari arayuz simgesi altinda kalan 'Lv' (12-13 px) da kabul: hemen sagi maskeli olmali
        kesik = maske is not None and 12 <= w < 14 and maske[y:y + hh, x + w:x + w + 4].any()
        if not ((14 <= w <= 55 or kesik) and 6 <= hh <= 15):
            continue
        # dar + uzun 'Lv' = kilic parlamasi (yesil-camgobegi L bicimi; 121949: w 19, h 14 -> sahte 'Lv + mavi'
        # oyuncu). Capa olcumu (ham karelerin 1/4'u, n=651): w %1 = 22, h 8-10 (%98); gozle bakilan 24 tuhaf
        # capada (h >= 11 ya da w < 20) h >= 11 gercekler ust uste binmis etiketler ve hepsi w >= 29.
        if w < 20 and hh >= 12 and not kesik:
            continue
        p = m[y:y + hh, x:x + w]
        if p.sum() < 12 or p[:, :3].any(axis=1).sum() < 6:      # 'L': solda en az 6 satirlik dikey cizgi
            continue
        sonuc.append((int(x), int(y), int(x + w), int(y + hh)))
    return sonuc


def _capa_etiketi(h, capa, capalar, gen, gri=None, maske=None):
    """Lv capasinin sagindaki ayni satiri ayristirip etiketi siniflar."""
    x0, y0, x1, y1 = capa
    r0, r1 = max(0, y0 - 2), y1 + 3                  # ad satiri: Lv ile ayni, alt cikintilar (s, c, g) +3
    son = min(gen, x1 + 340)
    for c in capalar:                                # sagda ayni satirda baska Lv: yeni etiket baslar
        if c[0] > x1 and c[1] < r1 and c[3] > r0:
            son = min(son, c[0] - 1)
    if son - x1 < 8:
        return None
    say = _say(h[r0:r1, x1:son])
    say[LV - 1] = 0
    parca, onceki = [], x1
    # maskeli (arayuz) sutunlar bosluk sayilmaz: etiket simgenin altindan devam edebilir
    ortulu = maske[r0:r1, x1:son].all(axis=0) if maske is not None else np.zeros(son - x1, bool)
    for p in _kosular(say, x1):
        if p[1] - onceki - ortulu[onceki - x1:p[1] - x1].sum() > 18:   # buyuk bosluk: etiket bitti
            break
        parca.append(p)
        onceki = p[2]
    onemli = [p for p in parca if p[2] - p[1] >= 8 and p[3] >= 12]
    if not onemli:
        return None
    bitis = onemli[-1][2]
    satirlar = np.where((h[r0:r1, x0:bitis] > 0).sum(axis=1) > 1)[0]
    ey0, ey1 = (r0 + satirlar[0], r0 + satirlar[-1] + 1) if len(satirlar) else (y0, y1)
    renkler = {p[0] for p in onemli}
    ad = "+".join(RENK_ADI[p[0]] for p in onemli)
    if renkler == {KIRMIZI}:
        return (x0, ey0, bitis, ey1, "yaratik", 0.9, "Lv + kirmizi ad")
    if renkler == {BEYAZ}:
        puan = 0.0
        if gri is not None:
            bolge = gri[max(0, ey0 - 5):ey1 + 5, x1:bitis + 5]
            if bolge.shape[0] >= MET_SABLON.shape[0] and bolge.shape[1] >= MET_SABLON.shape[1]:
                puan = float(cv2.matchTemplate(bolge, MET_SABLON, cv2.TM_CCOEFF_NORMED).max())
        if puan >= MET_ESIK:
            return (x0, ey0, bitis, ey1, "metin", 0.9, f"Lv + beyaz ad, 'Met' sablonu {puan:.2f}")
        if bitis - x1 <= 95:                         # olculen metin adi beyaz kismi 72-84 px
            return (x0, ey0, bitis, ey1, "metin", 0.6, f"Lv + beyaz ad (kisa), 'Met' sablonu {puan:.2f}")
        return (x0, ey0, bitis, ey1, "konusma", 0.5, "Lv + uzun beyaz yazi: konusma balonu")
    if renkler == {YESIL}:
        return None                                  # yesil ad onunde yanlis Lv parcasi: NPC taramasi bakar
    # Lv + kirmizi ad + uzun beyaz yazi: yaratigin ustune binmis konusma balonu (oyuncu adi <= ~75 px)
    if (onemli[0][0] == KIRMIZI and {p[0] for p in onemli[1:]} == {BEYAZ}
            and onemli[-1][2] - onemli[1][1] >= 90):
        kir_son = max(p[2] for p in onemli if p[0] == KIRMIZI)
        return (x0, ey0, kir_son, ey1, "yaratik", 0.75, "Lv + kirmizi ad (ustunde konusma balonu)")
    return (x0, ey0, bitis, ey1, "oyuncu", 0.85, "Lv + " + ad)


def _tire_var(h, x0, y0, x1, y1):
    """Yesil yazida 'Sahip - Evcil' tiresi: orta yukseklikte, en cok 6 px genis / 2 px kalin kucuk leke,
    iki yaninda en az 3 bos sutun. JPEG'de tire yesil / Lv / beyaz tonlarina dagilir: ucu de sayilir."""
    m = np.isin(h[y0:y1, x0:x1], (YESIL, LV, BEYAZ))
    yy = m.shape[0]
    if yy < 6:
        return False
    sut = m.sum(axis=0)
    dolu = np.where(sut > 0)[0]
    if len(dolu) < 3:
        return False
    # nonzero sutun kosulari
    kosu, bas_ = [], dolu[0]
    for a, b in zip(dolu[:-1], dolu[1:]):
        if b - a > 1:
            kosu.append((bas_, a))
            bas_ = b
    kosu.append((bas_, dolu[-1]))
    for i in range(1, len(kosu) - 1):
        a, b = kosu[i]
        if b - a + 1 > 6 or kosu[i][0] - kosu[i - 1][1] - 1 < 3 or kosu[i + 1][0] - b - 1 < 3:
            continue
        p = m[:, a:b + 1]
        satir = np.where(p.any(axis=1))[0]
        if p.sum() >= 2 and sut[a:b + 1].max() <= 2 and satir[-1] - satir[0] <= 1                 and 0.28 * yy <= satir.mean() <= 0.75 * yy:
            return True
    return False


def yesil_etiketler(h, kapali):
    """Lv'siz yesil adlar: NPC (ya da 'Sahip - Evcil' bicimli evcil hayvan / binek adi).
    Olcum: normal sozcuk arasi 4-6 px; 'Sahip - Evcil' de tire JPEG'de cogu kez kaybolur ve 13-15 px bosluk kalir."""
    m = ((h == YESIL) & ~kapali).astype(np.uint8)
    d = cv2.dilate(m, np.ones((3, 21), np.uint8))           # 'Sahip - Evcil' boslugu (<= 18 px) tek bilesen
    n, _, ist, _ = cv2.connectedComponentsWithStats(d, 8)
    sonuc = []
    for i in range(1, n):
        x, y, w, hh, _ = ist[i]
        if w < 20 or hh < 7 or hh > 160:
            continue
        for b0, b1 in _seritler(m, x, y, x + w, y + hh):
            if not 7 <= b1 - b0 <= 18:
                continue
            sut = m[b0:b1, x:x + w].sum(axis=0)
            dolu = np.where(sut > 0)[0]
            if not len(dolu):
                continue
            # sutun kosulari; 18 px'e kadar bosluk ayni etiket, buyuk bosluk ayri etiket
            parca = [[dolu[0], dolu[0], [], int(sut[dolu[0]])]]
            for j in dolu[1:]:
                bos = j - parca[-1][1] - 1
                if bos <= 18:
                    if bos >= 10:
                        parca[-1][2].append(bos)
                    parca[-1][1] = j
                    parca[-1][3] += int(sut[j])
                else:
                    parca.append([j, j, [], int(sut[j])])
            for a, b, bosluk, p in parca:
                xa, xb = x + a, x + b + 1
                if xb - xa < 20 or p < 25:
                    continue
                if bosluk or _tire_var(h, xa, b0, xb, b1):
                    sonuc.append((xa, b0, xb, b1, "evcil", 0.7, "yesil ad, 'Sahip - Evcil' (tire / genis bosluk)"))
                else:
                    sonuc.append((xa, b0, xb, b1, "npc", 0.75, "yesil ad, Lv yok"))
    return sonuc


def kenar_kirmizilar(h, kapali):
    """Sol ekran kenarina dayanan, Lv'si ekran disinda kalmis kirmizi adlar (yalniz kirmizi; sagda baska renk yok)."""
    m = ((h == KIRMIZI) & ~kapali).astype(np.uint8)
    m[:, 40:] = 0
    n, _, ist, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((3, 11), np.uint8)), 8)
    sonuc = []
    for i in range(1, n):
        x, y, w, hh, _ = ist[i]
        if x > 3 or not 7 <= hh <= 18:
            continue
        say = _say(h[y:y + hh, 0:min(h.shape[1], 300)])
        say[LV - 1] = 0
        parca, onceki = [], 0
        for p in _kosular(say, 0):
            if p[1] - onceki > 18:
                break
            parca.append(p)
            onceki = p[2]
        onemli = [p for p in parca if p[2] - p[1] >= 8 and p[3] >= 12]
        if onemli and {p[0] for p in onemli} == {KIRMIZI} and onemli[-1][2] >= 20:
            sonuc.append((0, y, onemli[-1][2], y + hh, "yaratik", 0.6, "kirmizi ad, Lv ekran disinda (sol kenar)"))
    return sonuc


def satir_etiketleri(rgb, h, maske, gri=None):
    """Renkli yazi satirlarindan etiketler: [(x0, y0, x1, y1, sinif, guven, aciklama)]"""
    yuk, gen = h.shape
    hh_ = np.where(maske, 0, h).astype(np.uint8)
    capalar = lv_capalari(hh_, maske)
    if gri is None:
        gri = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    sonuc = [e for e in (_capa_etiketi(hh_, c, capalar, gen, gri, maske) for c in capalar) if e]
    kapali = np.zeros((yuk, gen), bool)
    for e in sonuc:
        kapali[e[1]:e[3], e[0]:e[2]] = True
    return sonuc + yesil_etiketler(hh_, kapali) + kenar_kirmizilar(hh_, kapali)


# ---------------------------------------------------------------- ana islev
def kendimi_isaretle(etiketler, yuk, gen, gri=None):
    """Kendi karakterimizin etiketini 'kendim' yapar: once 'SaMRicKeTs' ad sablonu (her yerde), tutmazsa
    ekran ortasindaki (karakterin basi) Lv'li etiket. Konusma balonu adimizin yerine gecebilir."""
    adaylar = [i for i, e in enumerate(etiketler) if e[4] in ("oyuncu", "metin", "konusma")]
    if gri is not None:
        en, en_i = 0.0, None
        for i in adaylar:
            e = etiketler[i]
            b = gri[max(0, e[1] - 4):e[3] + 4, max(0, e[0]):e[2] + 4]
            if b.shape[0] >= AD_SABLON.shape[0] and b.shape[1] >= AD_SABLON.shape[1]:
                p = float(cv2.matchTemplate(b, AD_SABLON, cv2.TM_CCOEFF_NORMED).max())
                if p > en:
                    en, en_i = p, i
        if en >= AD_ESIK:
            e = etiketler[en_i]
            etiketler[en_i] = (e[0], e[1], e[2], e[3], "kendim", 0.95, f"ad sablonu {en:.2f}: " + e[6])
            return etiketler
    hedef = (gen // 2 - 35, 0.44 * yuk)
    aday = [i for i in adaylar if abs((etiketler[i][0] + etiketler[i][2]) / 2 - hedef[0]) <= 75
            and 0.37 * yuk <= (etiketler[i][1] + etiketler[i][3]) / 2 <= 0.49 * yuk]
    if aday:
        i = min(aday, key=lambda i: abs((etiketler[i][0] + etiketler[i][2]) / 2 - hedef[0])
                + abs((etiketler[i][1] + etiketler[i][3]) / 2 - hedef[1]))
        e = etiketler[i]
        etiketler[i] = (e[0], e[1], e[2], e[3], "kendim", 0.7, "ekran ortasi (ad sablonu tutmadi): " + e[6])
    return etiketler


def ad_etiketleri(rgb):
    """Ekrandaki her ad / tabela kutusu ve sinifi.
    Donus: [dict(x0, y0, x1, y1, sinif, guven, aciklama)] (kutu: yazinin / cercevenin kendisi)."""
    yuk, gen = rgb.shape[:2]
    maske = arayuz_maskesi(yuk, gen) | pencere_maskesi(rgb) | duyuru_maskesi(rgb)
    # ust ortadaki hedef penceresi yalniz aciksa (olcum: acik 0.86-0.87, kapali < 0.4 koyu oran)
    if (rgb[18:56, gen // 2 - 260:gen // 2 + 260].max(axis=2) < 60).mean() >= 0.6:
        maske[:70, gen // 2 - 290:gen // 2 + 290] = True
    sol_alt = np.zeros((yuk, gen), bool)
    sol_alt[yuk - 230:, 120:310] = True       # Vote4Buff simgesi / indirim penceresi: yalniz kutu aramasinda
    kutu = kutular(rgb, maske | sol_alt)
    h = renk_haritasi(rgb)
    ic = np.zeros((yuk, gen), bool)
    for k in kutu:                                   # kutu icindeki yazi satir analizine girmesin
        ic[max(0, k[1]):k[3] + 1, max(0, k[0]):k[2] + 1] = True
    gri = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    satir = satir_etiketleri(rgb, h, maske | ic, gri)
    hepsi = [e for e in kendimi_isaretle(satir, yuk, gen, gri) if e[4] != "konusma"] + kutu
    return [dict(x0=int(e[0]), y0=int(e[1]), x1=int(e[2]), y1=int(e[3]), sinif=e[4],
                 guven=round(float(e[5]), 2), aciklama=e[6]) for e in hepsi]


# ---------------------------------------------------------------- cizim / deneme
RENK_CIZ = {"yaratik": (255, 40, 40), "metin": (255, 255, 255), "npc": (40, 255, 40), "oyuncu": (255, 220, 0),
            "pazar": (255, 0, 255), "esya": (0, 200, 255), "kendim": (128, 128, 128), "evcil": (0, 128, 0)}


def ciz(rgb, etiketler):
    c = rgb.copy()
    for e in etiketler:
        r = RENK_CIZ.get(e["sinif"], (255, 255, 255))
        cv2.rectangle(c, (e["x0"] - 2, e["y0"] - 2), (e["x1"] + 2, e["y1"] + 2), r, 2)
        cv2.putText(c, e["sinif"], (e["x0"], e["y0"] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(c, e["sinif"], (e["x0"], e["y0"] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, r, 1)
    return c


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("kullanim: python ad_siniflari.py kare.jpg [cikti.jpg]")
        sys.exit(1)
    bgr = cv2.imread(sys.argv[1])
    if bgr is None:
        print("okunamadi:", sys.argv[1])
        sys.exit(1)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    import time
    t = time.time()
    et = ad_etiketleri(rgb)
    sure = time.time() - t
    for e in sorted(et, key=lambda e: (e["sinif"], e["y0"])):
        print(f"{e['sinif']:8s} ({e['x0']},{e['y0']})-({e['x1']},{e['y1']})  guven {e['guven']:.2f}  {e['aciklama']}")
    say = {}
    for e in et:
        say[e["sinif"]] = say.get(e["sinif"], 0) + 1
    print(f"{len(et)} etiket {say}  ({sure * 1000:.0f} ms)")
    if len(sys.argv) > 2:
        cikti = sys.argv[2]
    else:                                            # veri klasorunu kirletme: cizim goruntu/ad_test altina
        klasor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goruntu", "ad_test")
        os.makedirs(klasor, exist_ok=True)
        cikti = os.path.join(klasor, os.path.splitext(os.path.basename(sys.argv[1]))[0] + "_ad.jpg")
    cv2.imwrite(cikti, cv2.cvtColor(ciz(rgb, et), cv2.COLOR_RGB2BGR))
    print("cizim:", cikti)
