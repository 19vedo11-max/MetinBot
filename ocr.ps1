param([string]$Yol, [string]$Dil = "tr")
# Windows'un yerlesik OCR'i ile bir goruntudeki kelimeleri ve konumlarini JSON olarak yazar.
$wr = [System.Reflection.Assembly]::LoadWithPartialName('System.Runtime.WindowsRuntime')
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]
$asTask = ($wr.GetType('System.WindowsRuntimeSystemExtensions').GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Bekle($op, $tip) { $t = $asTask.MakeGenericMethod($tip).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
$dosya = Bekle ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Yol)) ([Windows.Storage.StorageFile])
$akis = Bekle ($dosya.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$coz = Bekle ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($akis)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Bekle ($coz.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$motor = $null
try { $motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($Dil)) } catch {}
if ($null -eq $motor) { $motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
$sonuc = Bekle ($motor.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
$cikti = @()
foreach ($satir in $sonuc.Lines) {
  foreach ($k in $satir.Words) {
    $r = $k.BoundingRect
    $cikti += [pscustomobject]@{ m = $k.Text; x = [int]$r.X; y = [int]$r.Y; g = [int]$r.Width; h = [int]$r.Height; satir = $satir.Text }
  }
}
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
ConvertTo-Json -InputObject @($cikti) -Compress
