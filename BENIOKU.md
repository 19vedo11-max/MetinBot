# MetinBot (Waryong2) - Paylasim Paketi

Ekran goruntusu okuyarak calisan kasilma botu. Yalnizca Windows.

## Kurulum
1. Zip'i bir klasore ac (ornek: `C:\MetinBot`). Gecici/okunamaz bir yere acma.
2. `Kur.bat` dosyasina cift tikla. Python 3.11+ yoksa kurmayi sorar; paketleri kurar, `ayar.json` olusturur, masaustune "MetinBot" kisayolu koyar.
3. Oyunu ac, **pencere modunda, yaklasik 1920x1080** ayarla (bot oyun penceresinin istemci alanini okur; arayuz sablonlari ve konum olculeri bu cozunurluk civarinda alinmistir, cok farkli boyutta sablon eslesmeleri tutmayabilir). Pencere ekran disina tasmasin.
4. `Bot-Baslat.bat` dosyasina **sag tik - Yonetici olarak calistir** (oyun yonetici yetkisiyle calistigi icin sart).
5. Masaustundeki "MetinBot" kisayolu ile paneli ac (http://localhost:8765).

## Ilk ayarlar
- Panelde **Beceriler** bolumunden sinifinin beceri/pot tuslarini gir.
- Kasilma alani, hedefler ve profil de panelden ayarlanir. `ayar_ornek.json` bos baslangic degerleridir.

## Tuslar
- **F10**: botu duraklat / devam ettir
- **F12**: botu kapat

## Notlar
- YOLO/torch egitim betikleri (`yolo_egit.py`, `gece_egit.py`) istege bagli ve pakette gerekli degildir; bot onlarsiz calisir.
- Windows'un yerlesik OCR'i kullanilir (Turkce/Ingilizce dil paketi yuklu olmali).

## Sorumluluk
Bot kullanimi oyun/sunucu kurallarina aykiri olabilir ve hesabinin kapatilmasina yol acabilir. Tum risk kullaniciya aittir; yazarlar sorumluluk kabul etmez.
