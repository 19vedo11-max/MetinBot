# Kontrol: X-AnyLabeling ile işaretleri düzeltme

Kısayolların hepsi X-AnyLabeling v4.3.3'ün kendi belgesinden (`docs/en/user_guide.md` §1.3, §2.1-2.3, §5.5, §7.1) ve varsayılan ayar dosyasından alındı.

## 1. Açma
1. İlk sefer: `araclar\X-AnyLabeling-Kur.bat` (programı `araclar\X-AnyLabeling\` içine kurar, 1-3 dk).
2. `araclar\Kontrol-Ac.bat` dosyasına çift tıkla. Program `veri_yolo\kontrol` klasörüyle açılır.
3. Sağ altta karelerin listesi var. İlk kareyi açmak için **D** tuşuna bas ya da listeden tıkla.
4. Arayüz İngilizce, Türkçe dil seçeneği yok.

Her kare `.jpg` dosyasının yanında aynı adlı bir `.json` var, kutular onun içinde.

## 2. Sınıflar (rakam tuşu = sınıf)
| Tuş | Sınıf | Renk | Ne |
|---|---|---|---|
| 0 | yaratik | kırmızı | canavar: adı KIRMIZI, solunda yeşil "Lv NN" |
| 1 | metin | mor | metin taşı |
| 2 | npc | yeşil | Biyolog, Satıcı, Demirci... (Lv yok) |
| 3 | oyuncu | mavi | başka oyuncular ("Lv NN" + unvan + ad) |
| 4 | pazar | turuncu | oyuncu dükkânı tabelası |
| 5 | esya | sarı | yere düşmüş eşya/yang |

**Kendi karakterin (SaMRicKeTs) asla kutulanmaz.** Üstünde kutu görürsen sil.

## 3. Her karede yapılacaklar
1. **Bak:** eksik kutu, fazla kutu, yanlış sınıf ya da kayık kutu var mı?
2. **Kutu ekle:** sınıfın rakamına bas (örn. `0`), bir köşeye sol tıkla, fareyi karşı köşeye götür, tekrar sol tıkla. Sınıf sorulmaz, rakama göre atanır.
   - Diğer yol: `R` tuşuna bas, kutuyu çiz, açılan listeden sınıfı seç, OK.
   - Çizimden vazgeçmek için `Esc`.
3. **Kutu sil:** kutuya tıklayıp seç, `Delete` tuşuna bas. Onay sorulmaz. Yanlışlıkla sildiysen `Ctrl+Z`.
4. **Sınıf değiştir:** kutuya çift tıkla (ya da seçip `Ctrl+E`), listeden doğru sınıfı seç, OK.
5. **Kutuyu düzelt:** seç, köşedeki tutamaçları sürükle. Ortasından sürüklersen kutu taşınır. Ok tuşlarıyla ince ayar yapabilirsin.
6. **Kaydet:** kayıt otomatik, her değişiklik anında `.json`'a yazılır. İstersen `Ctrl+S` de basabilirsin.
7. **Onayla ve sonraki kareye geç:** `Ctrl+Alt+K` kareyi "kontrol edildi" yapar (JSON'a `checked: true` yazılır), sonra `D` ile sonraki kareye geç. Önceki kare için `A`.
   - `Ctrl+Alt+K` çalışmazsa tuvalin sol altındaki **Passed** düğmesine bas ya da kareye sağ tıklayıp *Check Status > Passed* seç.

Seçme, silme ve çift tıklama **düzenleme modunda** çalışır. Kutu çizdikten sonra program bu moda kendisi geçer. Geçmezse `Ctrl+J` ile çizim ve düzenleme modları arasında geçebilirsin.

## 4. İşe yarar kısayollar
| Kısayol | İş |
|---|---|
| `D` / `A` | sonraki / önceki kare |
| `Ctrl+Shift+D` | sonraki onaylanmamış kare (kaldığın yerden devam) |
| `Ctrl+Alt+J` | kareyi "hatalı" işaretle (sonra bakılacak) |
| `Ctrl+Alt+U` | kare işaretini temizle |
| `Ctrl+Z` | geri al |
| `Esc` | çizimi iptal et / seçimi bırak |
| Fare tekerleği | yakınlaştır / uzaklaştır |
| `Ctrl+F` | kareyi pencereye sığdır |
| Sağ ya da orta tuşla sürükle | görüntüyü kaydır |
| `Ctrl+H` | tüm kutuları gizle / göster |
| `Ctrl+J` | çizim / düzenleme modu |

## 5. Dikkat
- `Ctrl+Delete` o karenin `.json` dosyasını **kalıcı olarak siler**, basma.
- `Ctrl+Shift+Delete` işe yaramaz bir kareyi (yükleme ekranı, menü) atar. Önce onay sorar. Resmi `veri_yolo\_delete_` klasörüne taşır, `.json`'unu ise **siler**. Program belgesi "ikisi de taşınır" diyor ama kaynak kod json'u siliyor (v4.3.3, `label_widget.py` `delete_image_file`).
- Ayarlar `araclar\xany_calisma\.xanylabelingrc` dosyasında. Ayarlarla (`Ctrl+0`) ya da rakam yöneticisiyle (`Alt+D`) oynayıp bir şeyi bozarsan bu dosyayı sil. `Kontrol-Ac.bat` onu `xany_ayar.yaml` şablonundan yeniden oluşturur.
- Sınıf listesi kilitli: listede olmayan bir ad yazılamaz, yazım hatası yeni sınıf açamaz.
- Programı kapatmadan önce kaydetmene gerek yok, her şey zaten kaydedilmiş olur.
