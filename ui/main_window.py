import os
import socket
import sys

import customtkinter as ctk

from core.logger import get_logger, register_log_callback
from core import config as cfg

log = get_logger("ui")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow:
    def __init__(self, snowflake_id: str, ws_port: int):
        self._snowflake_id = snowflake_id
        self._ws_port = ws_port
        self._ip_address = self._get_local_ip()

        self.root = ctk.CTk()
        self.root.title("ALAHA Program")
        self.root.geometry("500x600")
        self.root.resizable(False, False)

        self._build_ui()
        register_log_callback(self._append_log)

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            header,
            text="ALAHA Program",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Agente local — conecte pelo ALAHA Dashboard",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(anchor="w", pady=(2, 0))

        # SnowflakeID card
        id_frame = ctk.CTkFrame(self.root)
        id_frame.pack(fill="x", padx=24, pady=(12, 4))

        ctk.CTkLabel(
            id_frame,
            text="Seu SnowflakeID",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=16, pady=(14, 2))

        id_row = ctk.CTkFrame(id_frame, fg_color="transparent")
        id_row.pack(fill="x", padx=16, pady=(0, 14))

        self._id_label = ctk.CTkLabel(
            id_row,
            text=self._snowflake_id,
            font=ctk.CTkFont(size=16, weight="bold", family="Consolas"),
            text_color="#4488ff",
        )
        self._id_label.pack(side="left")

        ctk.CTkButton(
            id_row,
            text="Copiar",
            width=70,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._copy_id,
        ).pack(side="right")

        ctk.CTkLabel(
            self.root,
            text="Use o SnowflakeID e o IP desta máquina no ALAHA Dashboard.",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
        ).pack(padx=24, anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            self.root,
            text="Compartilhe também o IP abaixo ao cadastrar a máquina.",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
        ).pack(padx=24, anchor="w", pady=(0, 8))

        ip_frame = ctk.CTkFrame(self.root)
        ip_frame.pack(fill="x", padx=24, pady=(0, 4))

        ctk.CTkLabel(
            ip_frame,
            text="IP desta máquina",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=16, pady=(14, 2))

        ip_row = ctk.CTkFrame(ip_frame, fg_color="transparent")
        ip_row.pack(fill="x", padx=16, pady=(0, 14))

        self._ip_label = ctk.CTkLabel(
            ip_row,
            text=self._ip_address,
            font=ctk.CTkFont(size=16, weight="bold", family="Consolas"),
            text_color="#44cc88",
        )
        self._ip_label.pack(side="left")

        ctk.CTkButton(
            ip_row,
            text="Copiar",
            width=70,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._copy_ip,
        ).pack(side="right")

        # Status card
        status_frame = ctk.CTkFrame(self.root)
        status_frame.pack(fill="x", padx=24, pady=(4, 4))

        row_status = ctk.CTkFrame(status_frame, fg_color="transparent")
        row_status.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(row_status, text="Status:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self._status_label = ctk.CTkLabel(row_status, text="Conectando...", text_color="#ffaa00")
        self._status_label.pack(side="left", padx=10)

        row_llm = ctk.CTkFrame(status_frame, fg_color="transparent")
        row_llm.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(row_llm, text="LLM:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self._llm_label = ctk.CTkLabel(row_llm, text="—", text_color="gray")
        self._llm_label.pack(side="left", padx=10)

        row_port = ctk.CTkFrame(status_frame, fg_color="transparent")
        row_port.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(row_port, text="Porta:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(row_port, text=str(self._ws_port), text_color="#aaaaaa").pack(side="left", padx=10)

        # Autostart
        autostart_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        autostart_frame.pack(fill="x", padx=24, pady=(4, 0))

        _autostart_label = "Iniciar com o sistema" if sys.platform.startswith("linux") else "Iniciar com o Windows"
        self._autostart_var = ctk.BooleanVar(value=cfg.get_autostart())
        ctk.CTkCheckBox(
            autostart_frame,
            text=_autostart_label,
            variable=self._autostart_var,
            command=self._toggle_autostart,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w")

        # Logs
        ctk.CTkLabel(
            self.root,
            text="Logs",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(10, 2))

        self._log_box = ctk.CTkTextbox(self.root, height=110, state="disabled", font=ctk.CTkFont(size=11))
        self._log_box.pack(fill="both", padx=24, pady=(0, 20), expand=True)

    def _copy_id(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self._snowflake_id)
        log.info("SnowflakeID copiado para a area de transferencia")

    def _copy_ip(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self._ip_address)
        log.info("IP da maquina copiado para a area de transferencia")

    def _get_local_ip(self) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    def _toggle_autostart(self) -> None:
        enabled = self._autostart_var.get()
        cfg.set_autostart(enabled)
        if sys.platform.startswith("linux"):
            self._setup_linux_autostart(enabled)
        else:
            self._setup_windows_autostart(enabled)

    def _setup_windows_autostart(self, enabled: bool) -> None:
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                exe_path = sys.executable if getattr(sys, "frozen", False) else f'"{sys.executable}" "{os.path.abspath("main.py")}"'
                winreg.SetValueEx(key, "ALAHAProgram", 0, winreg.REG_SZ, exe_path)
                log.info("Autostart enabled in registry")
            else:
                try:
                    winreg.DeleteValue(key, "ALAHAProgram")
                    log.info("Autostart removed from registry")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            log.warning(f"Failed to set autostart: {e}")

    def _setup_linux_autostart(self, enabled: bool) -> None:
        try:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            desktop_file = os.path.join(autostart_dir, "alaha-program.desktop")
            if enabled:
                main_py = os.path.abspath("main.py")
                content = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=ALAHA Program\n"
                    f"Exec={sys.executable} {main_py}\n"
                    "Hidden=false\n"
                    "NoDisplay=false\n"
                    "X-GNOME-Autostart-enabled=true\n"
                )
                with open(desktop_file, "w") as f:
                    f.write(content)
                log.info("Autostart enabled via ~/.config/autostart")
            else:
                if os.path.exists(desktop_file):
                    os.remove(desktop_file)
                    log.info("Autostart removed from ~/.config/autostart")
        except Exception as e:
            log.warning(f"Failed to set autostart: {e}")

    def update_status(self, status: str) -> None:
        status_map = {
            "waiting": ("Aguardando conexao...", "#ffaa00"),
            "online": ("Conectado", "#22cc44"),
            "offline": ("Desconectado", "#ff4444"),
            "error": ("Erro", "#ff4444"),
        }
        display, color = status_map.get(status, (status.capitalize(), "gray"))

        def _update():
            self._status_label.configure(text=display, text_color=color)
        self.root.after(0, _update)

    def update_llm_status(self, model: str) -> None:
        def _update():
            self._llm_label.configure(text=model, text_color="#22cc44")
        self.root.after(0, _update)

    def _append_log(self, message: str) -> None:
        def _update():
            self._log_box.configure(state="normal")
            self._log_box.insert("end", message + "\n")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        try:
            self.root.after(0, _update)
        except Exception:
            pass

    def run(self) -> None:
        self.root.mainloop()

    def destroy(self) -> None:
        self.root.destroy()
