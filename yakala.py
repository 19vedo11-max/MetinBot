"""Oyun penceresinin goruntusunu alir (pencere arkada olsa da). Kullanim: python yakala.py [cikti.png]"""
import sys
import ctypes
import win32gui
import win32ui
from PIL import Image

ctypes.windll.user32.SetProcessDPIAware()
BASLIK = "Waryong2"


def pencere_bul():
    bulunan = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h) and BASLIK in win32gui.GetWindowText(h) and win32gui.GetClassName(h).startswith("eter"):
            bulunan.append(h)

    win32gui.EnumWindows(cb, None)
    return bulunan[0] if bulunan else None


def yakala(h):
    """Istemci alanini PIL Image olarak dondurur."""
    _, _, w, hgt = win32gui.GetClientRect(h)
    hdc = win32gui.GetDC(h)
    mdc = win32ui.CreateDCFromHandle(hdc)
    sdc = mdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mdc, w, hgt)
    sdc.SelectObject(bmp)
    # 1 = yalniz istemci alani, 2 = tam icerik (DirectX icin)
    ctypes.windll.user32.PrintWindow(h, sdc.GetSafeHdc(), 3)
    bilgi = bmp.GetInfo()
    veri = bmp.GetBitmapBits(True)
    img = Image.frombuffer("RGB", (bilgi["bmWidth"], bilgi["bmHeight"]), veri, "raw", "BGRX", 0, 1)
    win32gui.DeleteObject(bmp.GetHandle())
    sdc.DeleteDC()
    mdc.DeleteDC()
    win32gui.ReleaseDC(h, hdc)
    return img


if __name__ == "__main__":
    h = pencere_bul()
    if not h:
        sys.exit("Oyun penceresi bulunamadi")
    cikti = sys.argv[1] if len(sys.argv) > 1 else "goruntu/ekran.png"
    img = yakala(h)
    img.save(cikti)
    print(cikti, img.size, "ortalama parlaklik:", sum(img.convert("L").resize((64, 36)).getdata()) / (64 * 36))
