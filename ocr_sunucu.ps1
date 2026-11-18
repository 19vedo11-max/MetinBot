param([string]$Dil = "tr")
# Surekli calisan OCR sunucusu: stdin'den satir satir goruntu yolu alir, her biri icin tek satir JSON yazar.
# (ocr.ps1 her cagrida PowerShell'i bastan aciyordu: ~1 sn. Bu surec bir kez acilir, sonraki okumalar ~0.1 sn.)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$wr = [System.Reflection.Assembly]::LoadWithPartialName('System.Runtime.WindowsRuntime')
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.DataWriter, Windows.Storage.Streams, ContentType = WindowsRuntime]
$asTask = ($wr.GetType('System.WindowsRuntimeSystemExtensions').GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Bekle($op, $tip) { $t = $asTask.MakeGenericMethod($tip).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
$motor = $null
try { $motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($Dil)) } catch {}
if ($null -eq $motor) { $motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
[Console]::Out.WriteLine("HAZIR")
[Console]::Out.Flush()
while ($null -ne ($yol = [Console]::In.ReadLine())) {
  $json = "[]"
  $akis = $null
  try {
    # dosyayi bellege al (StorageFile ile acmak dosyayi kilitli birakiyordu; sonraki kayit basarisiz oluyordu)
    $bayt = [System.IO.File]::ReadAllBytes($yol.Trim())
    $akis = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    $yazici = New-Object Windows.Storage.Streams.DataWriter($akis)
    $yazici.WriteBytes($bayt)
    $null = Bekle ($yazici.StoreAsync()) ([UInt32])
    $null = $yazici.DetachStream()
    $akis.Seek(0)
    $coz = Bekle ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($akis)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bmp = Bekle ($coz.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $sonuc = Bekle ($motor.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
    $cikti = @()
    foreach ($satir in $sonuc.Lines) {
      foreach ($k in $satir.Words) {
        $r = $k.BoundingRect
        $cikti += [pscustomobject]@{ m = $k.Text; x = [int]$r.X; y = [int]$r.Y; g = [int]$r.Width; h = [int]$r.Height; satir = $satir.Text }
      }
    }
    $json = ConvertTo-Json -InputObject @($cikti) -Compress
    $bmp.Dispose()
  } catch { $json = "[]" }
  if ($null -ne $akis) { try { $akis.Dispose() } catch {} }
  [Console]::Out.WriteLine(($json -replace "[\r\n]+", " "))
  [Console]::Out.Flush()
}
