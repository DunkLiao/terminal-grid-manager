
"""
Open 4 Terminals
Python + ttk / Windows Terminal

需求：
- Windows 10 / 11
- Python 3.9+
- Windows Terminal (wt.exe)

不需要額外 pip install。
"""

import hashlib
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import tkinter as tk
import uuid

from pathlib import Path
from ctypes import wintypes
from tkinter import ttk, filedialog, messagebox


APP_NAME = "Open 4 Terminals"
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

CONFIG_FILE = APP_DIR / "open_4_terminals.json"
LEGACY_CONFIG_FILE = Path.home() / ".open_4_terminals.json"

DEFAULT_ITEMS = [
    {"name": "CMD 1", "folder": "", "command": ""},
    {"name": "CMD 2", "folder": "", "command": ""},
    {"name": "CMD 3", "folder": "", "command": ""},
    {"name": "CMD 4", "folder": "", "command": ""},
]


class TerminalManager(tk.Tk):
    def __init__(self):
        super().__init__()

        self.source_hash = self.get_source_hash()

        self.title(APP_NAME)
        window_height = max(
            480,
            min(620, self.winfo_screenheight() - 80)
        )
        self.geometry(f"850x{window_height}")
        self.minsize(720, 480)

        self.style = ttk.Style(self)
        self.setup_style()

        self.folder_vars = []
        self.command_vars = []
        self.layout = {"split_ratio": 0.5}

        self.build_ui()
        self.load_config()

    @staticmethod
    def get_source_hash():
        try:
            return hashlib.sha256(
                Path(__file__).resolve().read_bytes()
            ).hexdigest()
        except OSError:
            return None

    def restart_with_latest_source(self):
        current_hash = self.get_source_hash()
        if not current_hash or current_hash == self.source_hash:
            return False

        if not self.save_config(notify=False):
            return True

        script = Path(__file__).resolve()
        try:
            subprocess.Popen(
                [sys.executable, str(script), "--launch-terminals"],
                cwd=str(script.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=(
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                ),
            )
            self.destroy()
        except OSError as error:
            messagebox.showerror(
                "更新程式失敗",
                f"無法重新載入最新版本：\n\n{error}"
            )

        return True

    @staticmethod
    def get_visible_window_handles():
        user32 = ctypes.windll.user32
        handles = set()
        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM
        )
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL

        @callback_type
        def collect(hwnd, _lparam):
            if user32.IsWindowVisible(hwnd):
                handles.add(int(hwnd))
            return True

        user32.EnumWindows(collect, 0)
        return handles

    def activate_new_terminal_window(self, previous_handles, attempts=40):
        new_handles = (
            self.get_visible_window_handles() - previous_handles
        )

        if new_handles:
            hwnd = next(iter(new_handles))
            user32 = ctypes.windll.user32
            user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.ShowWindow.restype = wintypes.BOOL
            user32.SetForegroundWindow.argtypes = [wintypes.HWND]
            user32.SetForegroundWindow.restype = wintypes.BOOL
            user32.BringWindowToTop.argtypes = [wintypes.HWND]
            user32.BringWindowToTop.restype = wintypes.BOOL

            # SW_SHOWMAXIMIZED 會同時還原最小化視窗並最大化。
            user32.ShowWindow(hwnd, 3)
            if not user32.SetForegroundWindow(hwnd):
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
            return

        if attempts > 0 and self.winfo_exists():
            self.after(
                150,
                lambda: self.activate_new_terminal_window(
                    previous_handles,
                    attempts - 1
                )
            )

    def setup_style(self):
        themes = self.style.theme_names()

        if "vista" in themes:
            self.style.theme_use("vista")
        elif "clam" in themes:
            self.style.theme_use("clam")

        self.configure(bg="#F4F6F9")

        self.style.configure(
            "Title.TLabel",
            font=("Microsoft JhengHei UI", 17, "bold"),
            background="#F4F6F9",
            foreground="#202A33"
        )

        self.style.configure(
            "Info.TLabel",
            font=("Microsoft JhengHei UI", 10),
            background="#F4F6F9",
            foreground="#52616D"
        )

        self.style.configure(
            "TLabelframe.Label",
            font=("Microsoft JhengHei UI", 10, "bold")
        )

        self.style.configure(
            "TButton",
            font=("Microsoft JhengHei UI", 10),
            padding=5
        )

        self.style.configure(
            "Launch.TButton",
            font=("Microsoft JhengHei UI", 11, "bold"),
            padding=10
        )

    def build_ui(self):
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="Windows Terminal 四宮格管理器",
            style="Title.TLabel"
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="選擇四個工作資料夾，可分別指定 AI Coding CLI 啟動指令。",
            style="Info.TLabel"
        ).pack(anchor="w", pady=(5, 10))

        form_area = ttk.Frame(main)
        form_area.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            form_area,
            background="#F4F6F9",
            highlightthickness=0,
            borderwidth=0
        )
        scrollbar = ttk.Scrollbar(
            form_area,
            orient="vertical",
            command=canvas.yview
        )
        form = ttk.Frame(canvas)
        form_window = canvas.create_window(
            (0, 0),
            window=form,
            anchor="nw"
        )

        form.bind(
            "<Configure>",
            lambda _event: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(
                form_window,
                width=event.width
            )
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for i in range(4):
            self.create_terminal_group(form, i)

        button_frame = ttk.Frame(main)
        button_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(
            button_frame,
            text="儲存設定",
            command=self.save_config
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            button_frame,
            text="清除啟動指令",
            command=self.clear_commands
        ).pack(side="left")

        ttk.Button(
            button_frame,
            text="開啟四宮格",
            style="Launch.TButton",
            command=self.launch_terminals
        ).pack(side="right")

        self.status_var = tk.StringVar(
            value="就緒｜請選擇四個資料夾"
        )

        ttk.Label(
            main,
            textvariable=self.status_var,
            style="Info.TLabel"
        ).pack(anchor="w", pady=(6, 0))

    def create_terminal_group(self, parent, index):
        group = ttk.LabelFrame(
            parent,
            text=f"終端機 {index + 1}",
            padding=10
        )
        group.pack(fill="x", pady=4)

        folder_var = tk.StringVar()
        command_var = tk.StringVar()

        self.folder_vars.append(folder_var)
        self.command_vars.append(command_var)

        group.columnconfigure(1, weight=1)

        ttk.Label(
            group,
            text="工作資料夾"
        ).grid(row=0, column=0, padx=(0, 8), pady=3)

        ttk.Entry(
            group,
            textvariable=folder_var
        ).grid(
            row=0, column=1,
            sticky="ew",
            padx=(0, 8)
        )

        ttk.Button(
            group,
            text="瀏覽...",
            command=lambda i=index: self.browse_folder(i)
        ).grid(row=0, column=2)

        ttk.Label(
            group,
            text="啟動指令"
        ).grid(row=1, column=0, padx=(0, 8), pady=3)

        ttk.Entry(
            group,
            textvariable=command_var
        ).grid(
            row=1, column=1,
            sticky="ew",
            padx=(0, 8)
        )

        ttk.Label(
            group,
            text="可留空"
        ).grid(row=1, column=2)

    def browse_folder(self, index):
        current = self.folder_vars[index].get().strip()

        if os.path.isdir(current):
            initial = current
        else:
            initial = str(Path.home())

        folder = filedialog.askdirectory(
            title=f"選擇終端機 {index + 1} 的資料夾",
            initialdir=initial,
            mustexist=True
        )

        if folder:
            self.folder_vars[index].set(
                os.path.normpath(folder)
            )

    def get_config(self):
        return {
            "version": 2,
            "layout": self.layout,
            "terminals": [
                {
                    "name": f"CMD {i + 1}",
                    "folder": self.folder_vars[i].get().strip(),
                    "command": self.command_vars[i].get().strip()
                }
                for i in range(4)
            ]
        }

    def save_config(self, notify=True):
        try:
            data = self.get_config()

            with CONFIG_FILE.open(
                "w", encoding="utf-8"
            ) as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2
                )

            self.status_var.set(
                f"設定已儲存：{CONFIG_FILE}"
            )

            if notify:
                messagebox.showinfo(
                    "儲存成功",
                    "四組終端機設定已儲存。"
                )

            return True

        except OSError as error:
            messagebox.showerror(
                "儲存失敗",
                str(error)
            )
            return False

    def load_config(self):
        source_file = (
            CONFIG_FILE
            if CONFIG_FILE.exists()
            else LEGACY_CONFIG_FILE
        )
        if not source_file.exists():
            return

        try:
            with source_file.open(
                "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

            layout = data.get("layout", {})
            if isinstance(layout, dict):
                try:
                    split_ratio = float(
                        layout.get("split_ratio", self.layout["split_ratio"])
                    )
                    if 0.25 <= split_ratio <= 0.75:
                        self.layout["split_ratio"] = split_ratio
                except (TypeError, ValueError):
                    pass

            items = data.get("terminals", [])

            for i, item in enumerate(items[:4]):
                if not isinstance(item, dict):
                    continue

                self.folder_vars[i].set(
                    item.get("folder", "")
                )

                self.command_vars[i].set(
                    item.get("command", "")
                )

            if source_file == LEGACY_CONFIG_FILE:
                if self.save_config(notify=False):
                    self.status_var.set(
                        f"已載入舊設定並移至程式資料夾：{CONFIG_FILE}"
                    )
            else:
                self.status_var.set("已載入上次設定")

        except (OSError, ValueError, TypeError) as error:
            self.status_var.set(
                f"無法讀取舊設定：{error}"
            )

    def clear_commands(self):
        for variable in self.command_vars:
            variable.set("")

        self.status_var.set("已清除所有啟動指令")

    def validate_folders(self):
        folders = []

        for i, variable in enumerate(self.folder_vars):
            path = variable.get().strip().strip('"')

            if not path:
                messagebox.showwarning(
                    "資料夾未設定",
                    f"請選擇 CMD {i + 1} 的工作資料夾。"
                )
                return None

            path = os.path.abspath(
                os.path.expandvars(
                    os.path.expanduser(path)
                )
            )

            if not os.path.isdir(path):
                messagebox.showerror(
                    "資料夾不存在",
                    f"CMD {i + 1} 的路徑不存在：\n\n{path}"
                )
                return None

            folders.append(path)

        return folders

    @staticmethod
    def find_windows_terminal():
        # 常見情況：wt.exe 已在 PATH
        found = shutil.which("wt.exe")
        if found:
            return found

        # Windows App Execution Alias
        local_app_data = os.environ.get(
            "LOCALAPPDATA", ""
        )

        if local_app_data:
            candidate = os.path.join(
                local_app_data,
                "Microsoft",
                "WindowsApps",
                "wt.exe"
            )

            if os.path.isfile(candidate):
                return candidate

        return None

    @staticmethod
    def make_shell_args(folder, command):
        """
        回傳單一 pane 的設定：
        -d 指定工作目錄
        cmd.exe /k 保留終端機
        """
        args = ["-d", folder, "cmd.exe"]

        if command:
            args.extend(["/k", command])

        return args

    def launch_terminals(self):
        if self.restart_with_latest_source():
            return

        folders = self.validate_folders()
        if folders is None:
            return

        wt = self.find_windows_terminal()

        if not wt:
            messagebox.showerror(
                "找不到 Windows Terminal",
                "找不到 wt.exe。\n\n"
                "請先安裝 Windows Terminal，"
                "並確認 wt.exe 可以在 CMD 執行。"
            )
            return

        commands = [
            item.get().strip()
            for item in self.command_vars
        ]

        window_id = f"terminal_grid_{uuid.uuid4().hex}"
        split_size = str(self.layout["split_ratio"])
        previous_windows = self.get_visible_window_handles()

        # Windows Terminal 1.23/1.24 在單次 CLI 呼叫中連續建立多個
        # pane 時可能卡死。將每個 pane 操作拆開，逐一送到同一個具名視窗，
        # 並留出短暫間隔，避免 Terminal 同時處理多次版面配置。
        # 依序建立左右兩欄，再分別切分上下，形成閱讀順序的等分四宮格。
        wt_commands = [
            [
                wt, "-w", window_id, "--maximized", "--pos", "0,0",
                "new-tab",
                *self.make_shell_args(folders[0], commands[0]),
            ],
            [
                wt, "-w", window_id, "split-pane", "-V", "--size", split_size,
                *self.make_shell_args(folders[1], commands[1]),
            ],
            [wt, "-w", window_id, "move-focus", "left"],
            [
                wt, "-w", window_id, "split-pane", "-H", "--size", split_size,
                *self.make_shell_args(folders[2], commands[2]),
            ],
            [wt, "-w", window_id, "move-focus", "right"],
            [
                wt, "-w", window_id, "split-pane", "-H", "--size", split_size,
                *self.make_shell_args(folders[3], commands[3]),
            ],
        ]

        self.save_config(notify=False)

        try:
            for index, args in enumerate(wt_commands):
                subprocess.Popen(args, shell=False)
                if index < len(wt_commands) - 1:
                    time.sleep(1.0 if index == 0 else 0.2)

            self.after(
                150,
                lambda: self.activate_new_terminal_window(previous_windows)
            )
            self.status_var.set(
                "已送出 Windows Terminal 四宮格啟動指令"
            )

        except OSError as error:
            messagebox.showerror(
                "啟動失敗",
                f"無法啟動 Windows Terminal：\n\n{error}"
            )


def main():
    if sys.platform != "win32":
        print("此程式僅支援 Windows。")
        sys.exit(1)

    launch_after_start = "--launch-terminals" in sys.argv[1:]

    # 從 Windows Terminal 執行 `python open_4_terminals.py` 時，
    # Tkinter 的 mainloop 會佔住目前的前景終端工作階段。改由 pythonw
    # 啟動 GUI，讓原本的終端立即返回提示符。
    if Path(sys.executable).name.lower() == "python.exe":
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.is_file():
            pythonw = Path(shutil.which("pythonw.exe") or "")

        if pythonw.is_file():
            script = Path(__file__).resolve()
            subprocess.Popen(
                [str(pythonw), str(script), *sys.argv[1:]],
                cwd=str(script.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=(
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                ),
            )
            return

    app = TerminalManager()
    if launch_after_start:
        app.after(100, app.launch_terminals)
    app.mainloop()


if __name__ == "__main__":
    main()
