"""MetinBot Paneli: botu masaustunden yonetir (profil, ayarlar, baslat/duraklat/kapat, canli durum, gunluk)."""
import ctypes
import json
import os
import time
import tkinter as tk
from tkinter import messagebox, ttk

import kumanda

ZEMIN, KART, CIZGI = "#14161b", "#1d2028", "#2c303b"
YAZI, SOLUK, VURGU = "#e8e6df", "#8d93a3", "#d9a441"
YESIL, KIRMIZI, SARI = "#5fbf7a", "#d9534f", "#d9a441"

ANAHTARLAR = [  # (anahtar, etiket, profil ustune yaziyor mu)
    ("dusuk_seviye_kesme", "Seviyemden düşük yaratığı kesme, uygun bölgeye git", False),
    ("sadece_slot", "Yalnız slot kes (tek gezen yaratığa gitme)", False),
    ("esyaya_tikla", "Yere düşen eşyaları topla", False),
    ("olunce_yeniden_basla", "Ölünce kendisi kalksın", False),
    ("yeniden_baglan", "Oyundan atılınca yeniden bağlan", False),
    ("beceri_puani_dagit", "Beceri puanlarını dağıt", False),
    ("pot_satin_al", "Pot bitince köydeki Satıcı'dan al", False),
]
SAYILAR = [  # (anahtar, etiket, en az, en cok, adim, yuzde mi)
    ("can_esigi", "Can potu eşiği (%)", 10, 90, 5, True),
    ("mana_esigi", "Mana potu eşiği (%)", 0, 90, 5, True),
    ("seviye_ust_fark", "Benden en çok kaç seviye yüksek yaratık", 0, 50, 1, False),
    ("seviye_alt_fark", "Benden en çok kaç seviye düşük (exp veren)", 0, 15, 1, False),
    ("slot_en_az", "Slot sayılması için en az yaratık", 2, 8, 1, False),
    ("toplanacak_grup", "Kesmeden önce toplanacak grup sayısı", 1, 5, 1, False),
    ("pot_al_kirmizi_paket", "Kaç paket küçük kırmızı pot alsın (paket = 20)", 0, 10, 1, False),
    ("pot_al_mavi_paket", "Kaç paket küçük mavi pot alsın (paket = 20)", 0, 10, 1, False),
]
STATULER = [("str", "Güç (STR)"), ("vit", "Yaşam (VIT)"), ("dex", "Çeviklik (DEX)"), ("int", "Zekâ (INT)"), ("", "Dağıtma")]


class Panel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MetinBot Paneli")
        self.configure(bg=ZEMIN)
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=ZEMIN, foreground=YAZI, font=("Segoe UI", 10))
        st.configure("Kart.TFrame", background=KART)
        st.configure("Kart.TLabel", background=KART, foreground=YAZI)
        st.configure("Soluk.TLabel", background=KART, foreground=SOLUK, font=("Segoe UI", 9))
        st.configure("Baslik.TLabel", background=KART, foreground=VURGU, font=("Segoe UI Semibold", 11))
        st.configure("TCheckbutton", background=KART, foreground=YAZI)
        st.map("TCheckbutton", background=[("active", KART)], foreground=[("disabled", SOLUK)])
        st.configure("TRadiobutton", background=KART, foreground=YAZI, font=("Segoe UI Semibold", 10))
        st.map("TRadiobutton", background=[("active", KART)])
        st.configure("TButton", background=CIZGI, foreground=YAZI, borderwidth=0, padding=(14, 7))
        st.map("TButton", background=[("active", "#3a3f4d")])
        st.configure("Ana.TButton", background=VURGU, foreground="#17130a", font=("Segoe UI Semibold", 10))
        st.map("Ana.TButton", background=[("active", "#e8b655")])
        st.configure("TSpinbox", fieldbackground=ZEMIN, foreground=YAZI, arrowcolor=YAZI, bordercolor=CIZGI)
        st.configure("TCombobox", fieldbackground=ZEMIN, foreground=YAZI, arrowcolor=YAZI)
        st.map("TCombobox", fieldbackground=[("readonly", ZEMIN)], foreground=[("readonly", YAZI)])

        self.degisken, self.kutular = {}, {}
        self.profil = tk.StringVar(value="ozel")
        self.kirli = False
        self._ust()
        govde = tk.Frame(self, bg=ZEMIN)
        govde.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        govde.columnconfigure(0, weight=3, uniform="a")
        govde.columnconfigure(1, weight=2, uniform="a")
        govde.rowconfigure(0, weight=1)
        sol = tk.Frame(govde, bg=ZEMIN)
        sol.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        sag = tk.Frame(govde, bg=ZEMIN)
        sag.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self._plan(sol)
        self._gunluk(sol)
        self._ayarlar(sag)
        self.ayar_yukle()
        self.yenile()
        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())

    # ------------------------------------------------------------ ust serit
    def _ust(self):
        ust = ttk.Frame(self, style="Kart.TFrame", padding=(16, 12))
        ust.pack(fill="x", padx=14, pady=14)
        self.isik = tk.Canvas(ust, width=16, height=16, bg=KART, highlightthickness=0)
        self.isik.pack(side="left")
        self.nokta = self.isik.create_oval(2, 2, 14, 14, fill=SOLUK, outline="")
        self.durum_y = ttk.Label(ust, text="…", style="Kart.TLabel", font=("Segoe UI Semibold", 13))
        self.durum_y.pack(side="left", padx=(8, 18))
        ttk.Button(ust, text="Kapat", command=self.kapat).pack(side="right")
        self.dur_d = ttk.Button(ust, text="Duraklat", command=self.duraklat)
        self.dur_d.pack(side="right", padx=8)
        self.bas_d = ttk.Button(ust, text="Botu başlat", style="Ana.TButton", command=self.baslat)
        self.bas_d.pack(side="right")
        self.topla_d = ttk.Button(ust, text="Otomatik toplama: AÇ", style="Ana.TButton", command=self.hizli_toplama)
        self.topla_d.pack(side="right", padx=(0, 18))
        ttk.Button(ust, text="2. köye ışınlan", command=lambda: self.isinlan("koy2")).pack(side="right", padx=(0, 18))
        ttk.Button(ust, text="Harita…", command=self.harita_penceresi).pack(side="right", padx=(0, 6))
        ttk.Button(ust, text="1. köye ışınlan", command=lambda: self.isinlan("koy1")).pack(side="right", padx=(0, 6))
        self.bilgi_y = ttk.Label(self, text="", background=ZEMIN, foreground=SOLUK, font=("Segoe UI", 9))
        self.bilgi_y.pack(anchor="w", padx=30, pady=(0, 10))

    # ------------------------------------------------------------ gunluk plan
    def _plan(self, ana):
        k = ttk.Frame(ana, style="Kart.TFrame", padding=16)
        k.pack(fill="x")
        ttk.Label(k, text="BUGÜN NE YAPSIN", style="Baslik.TLabel").pack(anchor="w")
        for ad, etiket in kumanda.PROFILLER.items():
            ttk.Radiobutton(k, text=etiket, value=ad, variable=self.profil,
                            command=self.profil_degisti).pack(anchor="w", pady=(10, 0))
            ttk.Label(k, text=kumanda.PROFIL_ACIKLAMA[ad], style="Soluk.TLabel",
                      wraplength=500, justify="left").pack(anchor="w", padx=(24, 0))
        esya_s = ttk.Frame(k, style="Kart.TFrame")
        esya_s.pack(fill="x", pady=(14, 0))
        ttk.Label(esya_s, text="EŞYA AVI", style="Baslik.TLabel").pack(side="left")
        ttk.Button(esya_s, text="Eşya seç…", command=self.esya_penceresi).pack(side="right")
        self.esya_avi = ""
        self.esya_y = ttk.Label(k, text="", style="Soluk.TLabel", wraplength=500, justify="left")
        self.esya_y.pack(anchor="w")
        hedef_s = ttk.Frame(k, style="Kart.TFrame")
        hedef_s.pack(fill="x", pady=(14, 0))
        ttk.Label(hedef_s, text="YALNIZ ŞU CANAVARLAR", style="Baslik.TLabel").pack(side="left")
        ttk.Button(hedef_s, text="Canavar seç…", command=self.canavar_penceresi).pack(side="right")
        self.sadece_hedefler = []
        self.hedef_y = ttk.Label(k, text="", style="Soluk.TLabel", wraplength=500, justify="left")
        self.hedef_y.pack(anchor="w")
        ttk.Label(k, text="YANINDA", style="Baslik.TLabel").pack(anchor="w", pady=(16, 2))
        self.not_y = ttk.Label(k, text="", style="Soluk.TLabel")
        self.not_y.pack(anchor="w")
        for anahtar, etiket, aciklama in kumanda.YANINDA:
            v = tk.BooleanVar()
            c = ttk.Checkbutton(k, text=etiket, variable=v, command=self.dokunuldu)
            c.pack(anchor="w", pady=(6, 0))
            ttk.Label(k, text=aciklama, style="Soluk.TLabel").pack(anchor="w", padx=(24, 0))
            self.degisken[anahtar], self.kutular[anahtar] = v, c

    # ------------------------------------------------------------ ayarlar
    def _ayarlar(self, ana):
        k = ttk.Frame(ana, style="Kart.TFrame", padding=16)
        k.pack(fill="both", expand=True)
        ttk.Label(k, text="AYARLAR", style="Baslik.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Frame(k, style="Kart.TFrame", height=8).grid(row=1, column=0)
        r = 2
        for anahtar, etiket, _ in ANAHTARLAR:
            v = tk.BooleanVar()
            c = ttk.Checkbutton(k, text=etiket, variable=v, command=self.dokunuldu)
            c.grid(row=r, column=0, columnspan=2, sticky="w", pady=1)
            self.degisken[anahtar], self.kutular[anahtar] = v, c
            r += 1
        ttk.Frame(k, style="Kart.TFrame", height=8).grid(row=r, column=0)
        r += 1
        for anahtar, etiket, en_az, en_cok, adim, _ in SAYILAR:
            ttk.Label(k, text=etiket, style="Kart.TLabel").grid(row=r, column=0, sticky="w", pady=2)
            v = tk.StringVar()
            ttk.Spinbox(k, from_=en_az, to=en_cok, increment=adim, textvariable=v, width=6,
                        command=self.dokunuldu).grid(row=r, column=1, sticky="e")
            v.trace_add("write", lambda *_: self.dokunuldu())
            self.degisken[anahtar] = v
            r += 1
        ttk.Label(k, text="Statü puanı nereye", style="Kart.TLabel").grid(row=r, column=0, sticky="w", pady=2)
        self.statu = ttk.Combobox(k, values=[e for _, e in STATULER], state="readonly", width=16)
        self.statu.grid(row=r, column=1, sticky="e")
        self.statu.bind("<<ComboboxSelected>>", lambda _e: self.dokunuldu())
        r += 1
        ttk.Label(k, text="Beceri puanı sırası", style="Kart.TLabel").grid(row=r, column=0, sticky="w", pady=(12, 0))
        ttk.Button(k, text="Tıklayarak seç…", command=self.beceri_penceresi).grid(row=r, column=1, sticky="e",
                                                                                 pady=(12, 0))
        r += 1
        self.beceri_y = ttk.Label(k, text="", style="Soluk.TLabel", wraplength=440, justify="left")
        self.beceri_y.grid(row=r, column=0, columnspan=2, sticky="w")
        self.beceri_konum = []         # [[dx, dy], ...] kapat dugmesine gore ikon merkezleri, sirayla
        r += 1
        k.columnconfigure(0, weight=1)
        alt = ttk.Frame(k, style="Kart.TFrame")
        alt.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self.kaydet_d = ttk.Button(alt, text="Kaydet ve uygula", style="Ana.TButton", command=self.kaydet)
        self.kaydet_d.pack(side="right")
        self.kayit_y = ttk.Label(alt, text="", style="Soluk.TLabel")
        self.kayit_y.pack(side="left")

    # ------------------------------------------------------------ gunluk
    def _gunluk(self, ana):
        k = ttk.Frame(ana, style="Kart.TFrame", padding=16)
        k.pack(fill="both", expand=True, pady=(14, 0))
        ttk.Label(k, text="BOT NE YAPIYOR", style="Baslik.TLabel").pack(anchor="w")
        self.ozet_y = ttk.Label(k, text="", style="Kart.TLabel", justify="left", wraplength=500)
        self.ozet_y.pack(anchor="w", pady=(8, 10), fill="x")
        self.log = tk.Text(k, bg=ZEMIN, fg=YAZI, relief="flat", wrap="word", font=("Consolas", 9), height=7, width=60,
                           highlightthickness=1, highlightbackground=CIZGI, padx=8, pady=6)
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

    # ------------------------------------------------------------ veri
    def ayar_yukle(self):
        try:
            a = kumanda.ayar_oku()
        except Exception as e:
            messagebox.showerror("MetinBot", f"ayar.json okunamadı:\n{e}")
            return
        # eski "ozel" kaydi: metin tasi ayarina gore level ya da metin sayilir
        self.profil.set(a["profil"] if a.get("profil") in kumanda.PROFILLER
                        else ("metin" if a.get("metin_kes") else "level"))
        varsayilan = {"aranan_oncelik": True, "yeniden_baglan": True, "av_gorevi": True, "gorev_parsomen": True,
                      "dusuk_seviye_kesme": True, "pot_satin_al": True}
        for anahtar, _, _ in ANAHTARLAR + kumanda.YANINDA:
            self.degisken[anahtar].set(bool(a.get(anahtar, varsayilan.get(anahtar, False))))
        for anahtar, _, _, _, _, yuzde in SAYILAR:
            deger = a.get(anahtar, 0)
            self.degisken[anahtar].set(str(int(round(deger * 100))) if yuzde else str(int(deger)))
        self.beceri_konum = [list(q) for q in a.get("beceri_sira_konum", [])]
        self.beceri_ozet()
        self.esya_avi = a.get("esya_avi", "")
        self.esya_ozet()
        self.sadece_hedefler = list(a.get("sadece_hedefler", []))
        self.hedef_ozet()
        kod = a.get("statu", "str")
        self.statu.set(dict(STATULER).get(kod, STATULER[0][1]))
        self.profil_degisti(ilk=True)
        self.kirli = False
        self.kayit_y.configure(text="")

    def harita_penceresi(self):
        """Kayitli bolge haritalari (sekmeler); tiklanan noktaya bot yurur."""
        klasor = os.path.join(kumanda.KLASOR, "goruntu", "haritalar")
        os.makedirs(klasor, exist_ok=True)
        p = tk.Toplevel(self, bg=ZEMIN)
        p.title("Harita — tıkla, karakter oraya gitsin")
        p.transient(self)
        st = ttk.Style(p)
        st.configure("TNotebook", background=ZEMIN, borderwidth=0)
        st.configure("TNotebook.Tab", background=CIZGI, foreground=YAZI, padding=(12, 6))
        st.map("TNotebook.Tab", background=[("selected", VURGU)], foreground=[("selected", "#17130a")])
        ttk.Label(p, text="SAĞ TIK basılı tutup sürükle: kasılma alanı çiz (yeşil daire) — bot o alanın dışına çıkmadan slot keser.\n"
                          "Sol tık: karakter oraya yürür (oyun yolu kendisi bulur), varınca kesmeye devam eder.\n"
                          "Karakter o haritada değilse önce ışınlanmalısın. Yeni bölge için: o bölgedeyken “Bu haritayı kaydet”.",
                  background=ZEMIN, foreground=SOLUK, justify="left").pack(anchor="w", padx=14, pady=(12, 6))
        defter = ttk.Notebook(p)
        defter.pack(padx=14)
        durum_y = ttk.Label(p, text="", background=ZEMIN, foreground=VURGU)
        alan_v = tk.BooleanVar(value=bool(kumanda.ayar_oku().get("alan_kullan")))
        p._resimler = []
        OLCEK = 2

        def doldur():
            for sek in defter.tabs():
                defter.forget(sek)
            p._resimler.clear()
            dosyalar = sorted(f for f in os.listdir(klasor) if f.endswith(".png"))
            if not dosyalar:
                bos = tk.Frame(defter, bg=KART, width=508, height=200)
                defter.add(bos, text="(henüz harita yok)")
                tk.Label(bos, text="Kayıtlı harita yok.\nBot açıkken ve oyun öndeyken “Bu haritayı kaydet”e bas.",
                         bg=KART, fg=SOLUK).place(relx=0.5, rely=0.5, anchor="center")
                return
            for f in dosyalar:
                ad = f[:-4]
                resim = tk.PhotoImage(file=os.path.join(klasor, f)).zoom(OLCEK, OLCEK)
                p._resimler.append(resim)
                tuval = tk.Canvas(defter, width=resim.width(), height=resim.height(), bg=KART, highlightthickness=0,
                                  cursor="crosshair")
                tuval.create_image(0, 0, image=resim, anchor="nw")
                defter.add(tuval, text=ad)

                def tikla(e, ad=ad, tuval=tuval, w=resim.width(), hh=resim.height()):
                    if not kumanda.canli().get("ayakta"):
                        messagebox.showinfo("MetinBot", "Bot kapalı. Önce botu başlat.", parent=p)
                        return
                    tuval.delete("isaret")
                    tuval.create_oval(e.x - 7, e.y - 7, e.x + 7, e.y + 7, outline=VURGU, width=3, tags="isaret")
                    tuval.create_line(e.x - 11, e.y, e.x + 11, e.y, fill=VURGU, width=2, tags="isaret")
                    tuval.create_line(e.x, e.y - 11, e.x, e.y + 11, fill=VURGU, width=2, tags="isaret")
                    kumanda.git(ad, round(e.x / w, 4), round(e.y / hh, 4))
                    durum_y.configure(text=f"{ad}: işaretlenen noktaya gidiliyor… (bot logunda 'git:' satırına bak)")
                tuval.bind("<Button-1>", tikla)

                def alan_ciz(a_):
                    tuval.delete("alan")
                    if a_ and a_.get("harita") == ad:
                        cx_, cy_, r_ = a_["x"] * w_, a_["y"] * h_, a_["r"] * w_
                        tuval.create_oval(cx_ - r_, cy_ - r_, cx_ + r_, cy_ + r_, outline="#52d273", width=3, tags="alan")
                        tuval.create_text(cx_, cy_ - r_ - 9, text="kasılma alanı", fill="#52d273", tags="alan")

                w_, h_ = resim.width(), resim.height()
                bas_ = {}

                def sag_bas(e, bas_=bas_):
                    bas_["x"], bas_["y"] = e.x, e.y

                def sag_surukle(e, bas_=bas_, tuval=tuval):
                    r_ = max(8, ((e.x - bas_["x"]) ** 2 + (e.y - bas_["y"]) ** 2) ** 0.5)
                    tuval.delete("alan")
                    tuval.create_oval(bas_["x"] - r_, bas_["y"] - r_, bas_["x"] + r_, bas_["y"] + r_,
                                      outline="#52d273", width=3, dash=(4, 3), tags="alan")

                def sag_birak(e, bas_=bas_, ad=ad, w_=w_, h_=h_, alan_ciz=alan_ciz):
                    r_ = max(8, ((e.x - bas_["x"]) ** 2 + (e.y - bas_["y"]) ** 2) ** 0.5)
                    a_ = {"harita": ad, "x": round(bas_["x"] / w_, 4), "y": round(bas_["y"] / h_, 4), "r": round(r_ / w_, 4)}
                    kumanda.ayar_yaz({"kasilma_alani": a_, "alan_kullan": True})
                    alan_v.set(True)
                    alan_ciz(a_)
                    durum_y.configure(text=f"{ad}: kasılma alanı kaydedildi — bot bu dairenin dışına çıkmaz.")

                tuval.bind("<Button-3>", sag_bas)
                tuval.bind("<B3-Motion>", sag_surukle)
                tuval.bind("<ButtonRelease-3>", sag_birak)
                alan_ciz(kumanda.ayar_oku().get("kasilma_alani"))

        doldur()
        durum_y.pack(anchor="w", padx=14, pady=6)
        alt = tk.Frame(p, bg=ZEMIN)
        alt.pack(fill="x", padx=14, pady=(0, 12))

        def kaydet():
            if not kumanda.canli().get("ayakta"):
                messagebox.showinfo("MetinBot", "Bot kapalı. Önce botu başlat.", parent=p)
                return
            once = set(os.listdir(klasor))
            kumanda.komut("harita_kaydet")
            durum_y.configure(text="Bot haritayı açıp kaydediyor… (oyun önde olmalı)")

            def bekle(n=0):
                if set(os.listdir(klasor)) != once or n > 30:
                    doldur()
                    durum_y.configure(text="Harita kaydedildi." if n <= 30 else "Kaydedilemedi: oyun önde mi?")
                else:
                    p.after(1000, bekle, n + 1)
            p.after(2000, bekle)
        ttk.Button(alt, text="Bu haritayı kaydet", command=kaydet).pack(side="left")

        def alan_kaldir():
            kumanda.ayar_yaz({"kasilma_alani": None})
            doldur()
            durum_y.configure(text="Kasılma alanı kaldırıldı — bot yine kendisi bölge seçer.")
        ttk.Button(alt, text="Alanı kaldır", command=alan_kaldir).pack(side="left", padx=6)
        ttk.Checkbutton(alt, text="Çizdiğim alanda kal", variable=alan_v,
                        command=lambda: (kumanda.ayar_yaz({"alan_kullan": bool(alan_v.get())}),
                                         durum_y.configure(text="Bot artık yalnız çizilen alanda kasılır." if alan_v.get()
                                                           else "Alan kapalı: bot bölgeyi kendisi seçer (çizim saklı)."))
                        ).pack(side="left", padx=6)
        ttk.Button(alt, text="Kapat", command=p.destroy).pack(side="right")

    def hedef_ozet(self):
        self.hedef_y.configure(text=("Yalnız bunlar kesilir: " + ", ".join(self.sadece_hedefler))
                               if self.sadece_hedefler else "Kapalı — seviyeye uygun her canavar kesilir.")

    def canavar_penceresi(self):
        """Harita sekmelerinde canavar listesi; tikla-sec (✓). Listede olmayan ad elle eklenir."""
        try:
            with open(os.path.join(kumanda.KLASOR, "harita_bilgisi.json"), encoding="utf-8") as f:
                haritalar = json.load(f).get("haritalar", [])
        except Exception:
            haritalar = []
        try:
            with open(os.path.join(kumanda.KLASOR, "durum.json"), encoding="utf-8") as f:
                gorulen = sorted({a for v in json.load(f).get("bolge_ad", {}).values() for a in v
                                  if len(a) >= 6 and not any(c.isdigit() for c in a)})
        except Exception:
            gorulen = []
        secili = list(self.sadece_hedefler)
        p = tk.Toplevel(self, bg=ZEMIN)
        p.title("Yalnız şu canavarlar")
        p.transient(self)
        p.geometry("760x620")
        st = ttk.Style(p)
        st.configure("Treeview", background=KART, fieldbackground=KART, foreground=YAZI, rowheight=26,
                     font=("Segoe UI", 10), borderwidth=0)
        st.configure("Treeview.Heading", background=CIZGI, foreground=YAZI, font=("Segoe UI Semibold", 10))
        st.map("Treeview", background=[("selected", CIZGI)])
        st.configure("TNotebook", background=ZEMIN, borderwidth=0)
        st.configure("TNotebook.Tab", background=CIZGI, foreground=YAZI, padding=(12, 6))
        st.map("TNotebook.Tab", background=[("selected", VURGU)], foreground=[("selected", "#17130a")])
        ttk.Label(p, text="Kesilecek canavarlara tıkla (✓). Hiçbiri seçili değilse bot seviyeye uygun her canavarı keser.",
                  background=ZEMIN, foreground=SOLUK).pack(anchor="w", padx=14, pady=(12, 6))
        defter = ttk.Notebook(p)
        defter.pack(fill="both", expand=True, padx=14)
        agaclar = []

        def sekme(baslik, satirlar):
            cerceve = tk.Frame(defter, bg=KART)
            defter.add(cerceve, text=baslik)
            agac = ttk.Treeview(cerceve, columns=("lv",), show="tree headings", selectmode="none")
            agac.heading("#0", text="Canavar")
            agac.heading("lv", text="Lv")
            agac.column("#0", width=520)
            agac.column("lv", width=60, anchor="center")
            kay = ttk.Scrollbar(cerceve, orient="vertical", command=agac.yview)
            agac.configure(yscrollcommand=kay.set)
            agac.pack(side="left", fill="both", expand=True)
            kay.pack(side="right", fill="y")
            for ad, lv in satirlar:
                agac.insert("", "end", iid=f"{baslik}|{ad}", text=("✓  " if ad in secili else "     ") + ad, values=(lv,))

            def tikla(e, agac=agac):
                iid = agac.identify_row(e.y)
                if not iid:
                    return
                ad = iid.split("|", 1)[1]
                if ad in secili:
                    secili.remove(ad)
                else:
                    secili.append(ad)
                for a_ in agaclar:                         # ayni ad baska sekmede de varsa isaretini esitle
                    for i_ in a_.get_children():
                        n_ = i_.split("|", 1)[1]
                        a_.item(i_, text=("✓  " if n_ in secili else "     ") + n_)
                durum_y.configure(text=f"Seçili: {', '.join(secili) or 'yok'}")
            agac.bind("<Button-1>", tikla)
            agaclar.append(agac)

        for hrt in haritalar:
            if hrt.get("canavarlar"):
                sekme(hrt["ad"], [(ad, lv) for ad, lv in hrt["canavarlar"]])
        if gorulen:
            sekme("Oyunda görülen", [(ad, "") for ad in gorulen])
        alt = tk.Frame(p, bg=ZEMIN)
        alt.pack(fill="x", padx=14, pady=(8, 0))
        ttk.Label(alt, text="Listede yoksa adını yaz:", background=ZEMIN, foreground=YAZI).pack(side="left")
        giris_ = tk.Entry(alt, bg=ZEMIN, fg=YAZI, insertbackground=YAZI, relief="flat", highlightthickness=1,
                          highlightbackground=CIZGI, width=34, font=("Segoe UI", 10))
        giris_.pack(side="left", padx=8)

        def ekle():
            ad = giris_.get().strip()
            if ad and ad not in secili:
                secili.append(ad)
                durum_y.configure(text=f"Seçili: {', '.join(secili)}")
            giris_.delete(0, "end")
        ttk.Button(alt, text="Ekle", command=ekle).pack(side="left")
        durum_y = ttk.Label(p, text=f"Seçili: {', '.join(secili) or 'yok'}", background=ZEMIN, foreground=VURGU,
                            wraplength=720, justify="left")
        durum_y.pack(anchor="w", padx=14, pady=6)
        alt2 = tk.Frame(p, bg=ZEMIN)
        alt2.pack(fill="x", padx=14, pady=(0, 12))

        def tamam():
            self.sadece_hedefler = list(secili)
            self.hedef_ozet()
            self.dokunuldu()
            p.destroy()

        def temizle():
            secili.clear()
            for a_ in agaclar:
                for i_ in a_.get_children():
                    a_.item(i_, text="     " + i_.split("|", 1)[1])
            durum_y.configure(text="Seçili: yok")
        ttk.Button(alt2, text="Hepsini kaldır", command=temizle).pack(side="left")
        ttk.Button(alt2, text="Tamam", style="Ana.TButton", command=tamam).pack(side="right")

    def esya_ozet(self):
        self.esya_y.configure(text=f"Avlanan: {self.esya_avi} — düştüğü canavarlar öne alınır, görüldükleri bölgeye gidilir."
                              if self.esya_avi else "Kapalı. Seçersen bot o eşyanın düştüğü canavarlara odaklanır.")

    def esya_penceresi(self):
        """esya_avi.json'daki degerli esyalari kategori sekmelerinde gosterir; secilen esya avlanir."""
        try:
            with open(os.path.join(kumanda.KLASOR, "esya_avi.json"), encoding="utf-8") as f:
                esyalar = json.load(f).get("esyalar", [])
        except Exception:
            messagebox.showinfo("MetinBot", "Eşya tablosu (esya_avi.json) henüz yok.", parent=self)
            return
        p = tk.Toplevel(self, bg=ZEMIN)
        p.title("Eşya avı")
        p.transient(self)
        p.geometry("980x600")
        st = ttk.Style(p)
        st.configure("Treeview", background=KART, fieldbackground=KART, foreground=YAZI, rowheight=26,
                     font=("Segoe UI", 10), borderwidth=0)
        st.configure("Treeview.Heading", background=CIZGI, foreground=YAZI, font=("Segoe UI Semibold", 10))
        st.map("Treeview", background=[("selected", VURGU)], foreground=[("selected", "#17130a")])
        st.configure("TNotebook", background=ZEMIN, borderwidth=0)
        st.configure("TNotebook.Tab", background=CIZGI, foreground=YAZI, padding=(14, 6))
        st.map("TNotebook.Tab", background=[("selected", VURGU)], foreground=[("selected", "#17130a")])
        ttk.Label(p, text="Avlanacak eşyayı seç (çift tıkla ya da seçip “Bunu avla”). Kaynağı seviyenden yüksekse bot o canavarı kesemez.",
                  background=ZEMIN, foreground=SOLUK).pack(anchor="w", padx=14, pady=(12, 6))
        defter = ttk.Notebook(p)
        defter.pack(fill="both", expand=True, padx=14)
        agaclar = []
        kategoriler = []
        for e in esyalar:
            if e.get("kategori", "Diğer") not in kategoriler:
                kategoriler.append(e.get("kategori", "Diğer"))
        for kat in kategoriler:
            cerceve = tk.Frame(defter, bg=KART)
            defter.add(cerceve, text=kat)
            agac = ttk.Treeview(cerceve, columns=("lv", "sinif", "nereden"), show="tree headings", selectmode="browse")
            agac.heading("#0", text="Eşya")
            agac.heading("lv", text="Lv")
            agac.heading("sinif", text="Sınıf")
            agac.heading("nereden", text="Nereden düşer")
            agac.column("#0", width=230)
            agac.column("lv", width=50, anchor="center")
            agac.column("sinif", width=120)
            agac.column("nereden", width=520)
            kay = ttk.Scrollbar(cerceve, orient="vertical", command=agac.yview)
            agac.configure(yscrollcommand=kay.set)
            agac.pack(side="left", fill="both", expand=True)
            kay.pack(side="right", fill="y")
            for e in sorted((x for x in esyalar if x.get("kategori", "Diğer") == kat), key=lambda x: x.get("seviye") or 0):
                nereden = ", ".join(f"{k['ad']} (Lv {k.get('lv', '?')}, {k.get('harita', '?')})" for k in e.get("kaynaklar", []))
                ad = e["ad"] + (f" [{e['kisaltma']}]" if e.get("kisaltma") else "") + (" (tahmin)" if e.get("tahmin") else "")
                agac.insert("", "end", iid=e["ad"], text=ad, values=(e.get("seviye", ""), e.get("sinif", ""), nereden or "bilinmiyor"))
                if e["ad"] == self.esya_avi:
                    agac.selection_set(e["ad"])
            agaclar.append(agac)

        def sec(_e=None):
            for agac in agaclar:
                if agac.selection():
                    self.esya_avi = agac.selection()[0]
                    break
            self.esya_ozet()
            self.dokunuldu()
            p.destroy()

        for agac in agaclar:
            agac.bind("<Double-1>", sec)
            agac.bind("<<TreeviewSelect>>", lambda _e, a=agac: [x.selection_remove(x.selection()) for x in agaclar if x is not a])
        alt = tk.Frame(p, bg=ZEMIN)
        alt.pack(fill="x", padx=14, pady=12)

        def birak():
            self.esya_avi = ""
            self.esya_ozet()
            self.dokunuldu()
            p.destroy()

        ttk.Button(alt, text="Avı bırak", command=birak).pack(side="left")
        ttk.Button(alt, text="Bunu avla", style="Ana.TButton", command=sec).pack(side="right")

    def beceri_ozet(self):
        n = len(self.beceri_konum)
        self.beceri_y.configure(text=f"{n} beceri seçili: 1. sıradaki master olunca 2.'ye geçer. Seçilmeyene puan verilmez."
                                if n else "Seçili beceri yok — bot beceri puanı vermez.")

    def beceri_penceresi(self):
        """Oyundaki Yetenekler penceresinin resmini gosterir; becerilere puan verilecek SIRAYLA tiklanir."""
        resim_yolu = os.path.join(kumanda.KLASOR, "goruntu", "beceri_kirp.png")
        try:
            with open(os.path.join(kumanda.KLASOR, "durum.json"), encoding="utf-8") as f:
                koken = json.load(f).get("beceri_kirp_koken")
        except Exception:
            koken = None
        p = tk.Toplevel(self, bg=ZEMIN)
        p.title("Beceri sırası")
        p.transient(self)
        ttk.Label(p, text="Puan verilecek becerilere sırayla tıkla (ilk tıkladığın önce master olur).",
                  background=ZEMIN, foreground=YAZI).pack(anchor="w", padx=14, pady=(12, 2))
        bilgi = ttk.Label(p, text="", background=ZEMIN, foreground=SOLUK, font=("Segoe UI", 9))
        bilgi.pack(anchor="w", padx=14)
        tuval = tk.Canvas(p, bg=ZEMIN, highlightthickness=0, width=340, height=450)
        tuval.pack(padx=14, pady=8)
        secim = [list(q) for q in self.beceri_konum]
        durum_ = {"resim": None}

        def ciz():
            tuval.delete("all")
            if durum_["resim"] is not None:
                tuval.create_image(0, 0, image=durum_["resim"], anchor="nw")
            else:
                tuval.create_text(170, 200, text="Resim yok.\n“Oyundan yenile”ye bas\n(bot açık, oyun önde olmalı).",
                                  fill=SOLUK, justify="center")
            for i, (dx, dy) in enumerate(secim):
                x, y = dx - koken[0], dy - koken[1]
                tuval.create_oval(x - 12, y - 12, x + 12, y + 12, outline=VURGU, width=2)
                tuval.create_oval(x + 6, y - 20, x + 24, y - 2, fill=VURGU, outline="")
                tuval.create_text(x + 15, y - 11, text=str(i + 1), fill="#17130a", font=("Segoe UI Semibold", 9))
            bilgi.configure(text=f"{len(secim)} beceri seçildi" if secim else "Henüz seçilmedi")

        def yukle():
            nonlocal koken
            try:
                with open(os.path.join(kumanda.KLASOR, "durum.json"), encoding="utf-8") as f:
                    koken = json.load(f).get("beceri_kirp_koken")
                durum_["resim"] = tk.PhotoImage(file=resim_yolu) if koken and os.path.exists(resim_yolu) else None
            except Exception:
                durum_["resim"] = None
            if durum_["resim"] is not None:
                tuval.configure(width=durum_["resim"].width(), height=durum_["resim"].height())
            ciz()

        def tikla(e):
            if durum_["resim"] is None or not koken:
                return
            secim.append([e.x + koken[0], e.y + koken[1]])
            ciz()

        def yenile():
            if not kumanda.canli().get("ayakta"):
                messagebox.showinfo("MetinBot", "Bot kapalı. Önce botu başlat, oyunu öne al.", parent=p)
                return
            eski = os.path.getmtime(resim_yolu) if os.path.exists(resim_yolu) else 0
            kumanda.komut("beceri_goruntu")
            bilgi.configure(text="Bot oyunda Yetenekler penceresini açıyor… (oyun önde olmalı)")

            def bekle(n=0):
                if os.path.exists(resim_yolu) and os.path.getmtime(resim_yolu) > eski:
                    yukle()
                elif n < 30:
                    p.after(1000, bekle, n + 1)
                else:
                    bilgi.configure(text="Resim gelmedi: oyun önde mi, bot çalışıyor mu?")
            p.after(1500, bekle)

        def tamam():
            self.beceri_konum = secim
            self.beceri_ozet()
            self.dokunuldu()
            p.destroy()

        tuval.bind("<Button-1>", tikla)
        alt = tk.Frame(p, bg=ZEMIN)
        alt.pack(fill="x", padx=14, pady=(0, 12))
        ttk.Button(alt, text="Geri al", command=lambda: (secim.pop() if secim else None, ciz())).pack(side="left")
        ttk.Button(alt, text="Temizle", command=lambda: (secim.clear(), ciz())).pack(side="left", padx=6)
        ttk.Button(alt, text="Oyundan yenile", command=yenile).pack(side="left")
        ttk.Button(alt, text="Tamam", style="Ana.TButton", command=tamam).pack(side="right")
        yukle()

    def profil_degisti(self, ilk=False):
        hepsi = self.profil.get() == "gorev"                  # "Önce görevler": dört iş de zorunlu açık
        for anahtar, _, _ in kumanda.YANINDA:
            self.kutular[anahtar].state(["disabled"] if hepsi else ["!disabled"])
        self.not_y.configure(text="“Önce görevler” seçiliyken dördü de açık sayılır." if hepsi
                             else "Kasılırken bunlardan hangilerini de yapsın:")
        if not ilk:
            self.dokunuldu()

    def dokunuldu(self):
        self.kirli = True
        self.kayit_y.configure(text="Kaydedilmemiş değişiklik var", foreground=SARI)

    def kaydet(self):
        yeni = {"profil": self.profil.get()}
        for anahtar, _, _ in ANAHTARLAR + kumanda.YANINDA:
            yeni[anahtar] = bool(self.degisken[anahtar].get())
        try:
            for anahtar, etiket, en_az, en_cok, _, yuzde in SAYILAR:
                sayi = int(float(self.degisken[anahtar].get().replace(",", ".")))
                if not en_az <= sayi <= en_cok:
                    raise ValueError(f"“{etiket}” {en_az} ile {en_cok} arasında olmalı.")
                yeni[anahtar] = sayi / 100 if yuzde else sayi
        except ValueError as e:
            messagebox.showwarning("MetinBot", str(e) if "arasında" in str(e) else "Sayı alanlarından biri sayı değil.")
            return
        yeni["statu"] = {e: kod for kod, e in STATULER}.get(self.statu.get(), "str")
        yeni["beceri_sira_konum"] = self.beceri_konum
        yeni["esya_avi"] = self.esya_avi
        yeni["sadece_hedefler"] = self.sadece_hedefler
        yeni["beceri_sirasi"] = []         # konum listesi esas; bos secim = puan verme
        try:
            kumanda.ayar_yaz(yeni)
        except Exception as e:
            messagebox.showerror("MetinBot", f"Kaydedilemedi:\n{e}")
            return
        self.kirli = False
        ayakta = kumanda.canli().get("ayakta")
        self.kayit_y.configure(foreground=YESIL, text="Kaydedildi — bot birkaç saniyede yeni ayarla açılır"
                               if ayakta else "Kaydedildi — bot başlayınca geçerli olur")

    # ------------------------------------------------------------ komutlar
    def baslat(self):
        if kumanda.canli().get("ayakta"):
            kumanda.komut("devam")
            return
        bat = os.path.join(kumanda.KLASOR, "Bot-Baslat.bat")
        # oyun yonetici yetkisiyle calistigi icin bot da oyle acilmali: Windows onay penceresi cikar
        sonuc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f'/c "{bat}"', kumanda.KLASOR, 1)
        if sonuc <= 32:
            messagebox.showinfo("MetinBot", "Bot başlatılmadı (yönetici onayı verilmedi).")

    def hizli_toplama(self):
        """Tek tik: bot yalniz Z'ye basar (sen oynarsin). Aciksa kapatir."""
        d = kumanda.canli()
        if d.get("ayakta") and d.get("profil") == "toplama":
            kumanda.komut("kapat")
            return
        kumanda.ayar_yaz({"profil": "toplama"})
        self.profil.set("toplama")
        self.profil_degisti(ilk=True)
        if not d.get("ayakta"):
            self.baslat()                    # bot kapaliysa yonetici onayiyla acilir; aciksa ayar degisince kendini yeniden acar

    def isinlan(self, komut):
        if not kumanda.canli().get("ayakta"):
            messagebox.showinfo("MetinBot", "Bot kapalı. Işınlanmayı bot yapar; önce botu başlat.")
            return
        kumanda.komut(komut)

    def duraklat(self):
        d = kumanda.canli()
        if d.get("ayakta"):
            kumanda.komut("devam" if d.get("duraklat") else "duraklat")

    def kapat(self):
        if kumanda.canli().get("ayakta") and messagebox.askyesno(
                "MetinBot", "Bot kapatılsın mı?\nYeniden açmak için “Botu başlat” ve yönetici onayı gerekir."):
            kumanda.komut("kapat")

    # ------------------------------------------------------------ canli
    def yenile(self):
        d = kumanda.canli()
        yazi = kumanda.durum_yazisi(d)
        self.topla_d.configure(text="Otomatik toplama: KAPAT" if d.get("ayakta") and d.get("profil") == "toplama"
                               else "Otomatik toplama: AÇ")
        renk = {"ÇALIŞIYOR": YESIL, "DURAKLATILDI": SARI, "KAPALI": KIRMIZI}.get(yazi, SARI)
        self.isik.itemconfigure(self.nokta, fill=renk)
        self.durum_y.configure(text=yazi)
        if d.get("ayakta"):
            dk = (time.time() - d.get("baslangic", time.time())) / 60
            self.bilgi_y.configure(text=f"Seviye {d.get('seviye') or '?'}   ·   {d.get('kesilen', 0)} hedef / {dk:.0f} dk"
                                        f"   ·   plan: {kumanda.PROFILLER.get(d.get('profil'), '?')}")
            av = ", ".join(d.get("av_hedefi") or []) or "yok"
            aranan = ", ".join(d.get("aranan") or []) or "yok"
            self.ozet_y.configure(text=f"Plan: {d.get('plan') or '-'}\nEşya avı: {d.get('esya') or '-'}\n"
                                       f"Av görevi hedefi: {av}\nGörevden okunan yaratık: {aranan}")
            self.bas_d.configure(text="Devam ettir" if d.get("duraklat") else "Bot çalışıyor")
            self.bas_d.state(["!disabled"] if d.get("duraklat") else ["disabled"])
            self.dur_d.configure(text="Devam" if d.get("duraklat") else "Duraklat")
            self.dur_d.state(["!disabled"])
        else:
            self.bilgi_y.configure(text="Bot kapalı. Başlatınca Windows yönetici onayı ister.")
            self.ozet_y.configure(text="")
            self.bas_d.configure(text="Botu başlat")
            self.bas_d.state(["!disabled"])
            self.dur_d.state(["disabled"])
        satirlar = "\n".join(kumanda.log_sonu(40))
        if satirlar != getattr(self, "_son_log", None):
            self._son_log = satirlar
            self.log.configure(state="normal")
            self.log.delete("1.0", "end")
            self.log.insert("end", satirlar)
            self.log.see("end")
            self.log.configure(state="disabled")
        self.after(2000, self.yenile)


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    Panel().mainloop()
