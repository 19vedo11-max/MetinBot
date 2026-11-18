"""Sentetik tus oyuna ulasiyor mu? 'i' ile envanteri kapatip acar, oncesi/sonrasi goruntu alir."""
import ctypes
import time
import win32gui
import pydirectinput
from PIL import ImageGrab, ImageChops
import yakala

ctypes.windll.user32.SetProcessDPIAware()
h = yakala.pencere_bul()
onceki = win32gui.GetForegroundWindow()
ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
win32gui.SetForegroundWindow(h)
time.sleep(1.0)
x, y = win32gui.ClientToScreen(h, (0, 0))
_, _, w, hh = win32gui.GetClientRect(h)
kutu = (x, y, x + w, y + hh)
env = (1700, 330, 1920, 1060)  # envanter paneli bolgesi


def fark(a, b):
    d = ImageChops.difference(a.crop(env).convert("L"), b.crop(env).convert("L"))
    return sum(d.resize((44, 146)).tobytes()) / (44 * 146)


a = ImageGrab.grab(bbox=kutu)
pydirectinput.press("i")
time.sleep(0.8)
b = ImageGrab.grab(bbox=kutu)
pydirectinput.press("i")
time.sleep(0.8)
c = ImageGrab.grab(bbox=kutu)
b.save("goruntu/girdi_sonra.png")
print("i sonrasi envanter farki:", round(fark(a, b), 1), "| geri acinca fark:", round(fark(a, c), 1))
try:
    win32gui.SetForegroundWindow(onceki)
except Exception as e:
    print(e)
