"""BrownDust2 MOD Manager - 高级管理型界面（仅 Python 标准库）"""
from __future__ import annotations
import os, sys, string, queue, threading, subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "BrownDust2 MOD Manager"
TARGET = ("Neowiz", "Browndust2", "BrownDust2", "_10000002",
          "BepInEx", "plugins", "BrownDustX", "mods")
SKIP = {"$recycle.bin", "system volume information", "windows",
        "windowsapps", "node_modules", ".git"}

def matches_target(path):
    try:
        parts = Path(os.path.abspath(path)).parts
        return len(parts) >= len(TARGET) and tuple(
            p.casefold() for p in parts[-len(TARGET):]
        ) == tuple(p.casefold() for p in TARGET)
    except (OSError, ValueError):
        return False

def search_roots():
    roots = []
    home = Path.home()
    for p in [home / "Games", home / "AppData/Local/Programs",
              Path("C:/Program Files (x86)/Steam/steamapps"),
              Path("C:/Program Files/Steam/steamapps"), Path("C:/Steam"),
              Path("D:/SteamLibrary"), Path("D:/Steam"), Path("E:/SteamLibrary")]:
        try:
            if p.is_dir():
                roots.append(str(p))
        except OSError:
            pass
    if os.name == "nt":
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.isdir(drive):
                roots.append(drive)
    else:
        roots.extend(["/mnt", "/media", str(home)])
    return list(dict.fromkeys(roots))

def scan_mod_folders(status, found, stop):
    results, seen = [], set()
    roots = search_roots()
    status(f"开始扫描 {len(roots)} 个搜索起点；大型磁盘可能需要几分钟…")
    for root in roots:
        if stop.is_set():
            status("搜索已停止。")
            return
        status(f"正在扫描：{root}")
        try:
            for current, dirs, _files in os.walk(root, topdown=True, onerror=lambda _e: None):
                if stop.is_set():
                    status("搜索已停止。")
                    return
                dirs[:] = [d for d in dirs if d.casefold() not in SKIP]
                if Path(current).name.casefold() == "mods" and matches_target(current):
                    normalized = os.path.normpath(os.path.abspath(current))
                    key = os.path.normcase(normalized)
                    if key not in seen:
                        seen.add(key)
                        results.append(normalized)
                        found(list(results))
        except (PermissionError, OSError):
            continue
    status(f"扫描完成：找到 {len(results)} 个目标目录。" if results
           else "未找到目标目录。可以点击“选择目录”手动指定。")

class Manager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1120x720")
        self.minsize(900, 580)
        self.configure(bg="#17191e")
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.worker = None
        self.root_dir = ""
        self.items = []
        self.style_ui()
        self.build_ui()
        self.after(100, self.poll_events)

    def style_ui(self):
        s = ttk.Style(self)
        try: s.theme_use("clam")
        except tk.TclError: pass
        s.configure(".", font=("Segoe UI", 10))
        s.configure("Treeview", background="#20232a", foreground="#e7e8eb",
                    fieldbackground="#20232a", rowheight=30, borderwidth=0)
        s.configure("Treeview.Heading", background="#2b2f38", foreground="#f4f4f5",
                    font=("Segoe UI", 9, "bold"), relief="flat")
        s.map("Treeview", background=[("selected", "#765a32")],
              foreground=[("selected", "#ffffff")])
        s.configure("TProgressbar", troughcolor="#292c33", background="#c59a55")

    def label(self, parent, text, size=10, color="#e7e8eb", bold=False):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"))

    def button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command,
            bg="#a8793d" if primary else "#2b2f38",
            fg="#ffffff" if primary else "#e7e8eb",
            activebackground="#c18d4b", activeforeground="#ffffff",
            relief="flat", bd=0, padx=13, pady=8, cursor="hand2")

    def build_ui(self):
        top = tk.Frame(self, bg="#20232a", height=76)
        top.pack(fill="x"); top.pack_propagate(False)
        brand = tk.Frame(top, bg="#20232a"); brand.pack(side="left", padx=22, pady=12)
        self.label(brand, "BROWNDUST2", 9, "#c59a55", True).pack(anchor="w")
        self.label(brand, "MOD 管理器", 19, "#ffffff", True).pack(anchor="w")
        self.badge = self.label(top, "● 未扫描", 10, "#c59a55", True)
        self.badge.pack(side="right", padx=24)

        body = tk.Frame(self, bg="#17191e"); body.pack(fill="both", expand=True)
        side = tk.Frame(body, bg="#20232a", width=205); side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self.label(side, "工作区", 9, "#9297a2", True).pack(anchor="w", padx=18, pady=(24,10))
        self.nav = {}
        for key, title in [("overview","▦  总览"),("mods","▤  MOD 列表"),
                           ("paths","⌕  路径查找"),("settings","⚙  设置")]:
            b = tk.Button(side, text=title, anchor="w",
                command=lambda k=key: self.navigate(k),
                bg="#30343d" if key=="mods" else "#20232a",
                fg="#ffffff" if key=="mods" else "#c7cad1",
                activebackground="#30343d", activeforeground="#ffffff",
                relief="flat", bd=0, padx=18, pady=12, cursor="hand2")
            b.pack(fill="x", padx=8, pady=2); self.nav[key] = b
        tk.Frame(side, bg="#3a3e47", height=1).pack(fill="x", padx=16, pady=18)
        self.label(side, "当前 MOD 目录", 9, "#9297a2", True).pack(anchor="w", padx=18)
        self.side_path = self.label(side, "尚未定位", 9, "#d8d9dd")
        self.side_path.pack(anchor="w", padx=18, pady=7)
        self.side_path.configure(wraplength=165, justify="left")

        main = tk.Frame(body, bg="#17191e"); main.pack(side="left", fill="both", expand=True, padx=22, pady=20)
        head = tk.Frame(main, bg="#17191e"); head.pack(fill="x")
        hleft = tk.Frame(head, bg="#17191e"); hleft.pack(side="left", fill="x", expand=True)
        self.label(hleft, "MOD 控制台", 20, "#ffffff", True).pack(anchor="w")
        self.label(hleft, "定位 MOD 文件夹、查看文件信息并快速打开目录。", 10, "#9ca1ac").pack(anchor="w", pady=(5,0))
        self.button(head, "⌕ 自动查找", self.start_search, True).pack(side="right", padx=(8,0))
        self.button(head, "选择目录", self.choose_dir).pack(side="right")

        card = tk.Frame(main, bg="#20232a", padx=15, pady=13); card.pack(fill="x", pady=(20,14))
        self.label(card, "MOD 目录路径", 9, "#9ca1ac", True).pack(anchor="w")
        row = tk.Frame(card, bg="#20232a"); row.pack(fill="x", pady=(7,0))
        self.path_var = tk.StringVar(value="尚未找到目录")
        tk.Entry(row, textvariable=self.path_var, state="readonly",
            readonlybackground="#20232a", fg="#e7e8eb", bd=0,
            font=("Consolas", 10)).pack(side="left", fill="x", expand=True, ipady=4)
        self.button(row, "打开文件夹", self.open_dir).pack(side="right", padx=(10,0))

        metrics = tk.Frame(main, bg="#17191e"); metrics.pack(fill="x", pady=(0,14))
        self.metric = {}
        for key, title, initial in [("total","条目总数","—"),("files","文件","—"),
                                    ("folders","子目录","—"),("state","扫描状态","待开始")]:
            c = tk.Frame(metrics, bg="#20232a", padx=14, pady=12)
            c.pack(side="left", fill="both", expand=True, padx=(0,10))
            self.label(c, title, 9, "#9ca1ac").pack(anchor="w")
            var = tk.StringVar(value=initial); self.metric[key] = var
            tk.Label(c, textvariable=var, bg="#20232a", fg="#ffffff",
                font=("Segoe UI",17,"bold")).pack(anchor="w", pady=(5,0))

        listing = tk.Frame(main, bg="#20232a", padx=14, pady=12)
        listing.pack(fill="both", expand=True)
        lh = tk.Frame(listing, bg="#20232a"); lh.pack(fill="x", pady=(0,10))
        self.label(lh, "MOD 文件列表", 12, "#ffffff", True).pack(side="left")
        self.filter_var = tk.StringVar()
        ent = tk.Entry(lh, textvariable=self.filter_var, width=28, bg="#17191e",
            fg="#e7e8eb", insertbackground="#ffffff", relief="flat", bd=0)
        ent.pack(side="right", ipady=7, padx=(8,0))
        ent.bind("<KeyRelease>", lambda _e: self.render_items())
        self.label(lh, "过滤：", 9, "#9ca1ac").pack(side="right")
        cols = ("name","type","size","path")
        self.tree = ttk.Treeview(listing, columns=cols, show="headings", selectmode="browse")
        for col, title, width in [("name","文件名",260),("type","类型",90),
                                  ("size","大小",100),("path","位置",360)]:
            self.tree.heading(col,text=title); self.tree.column(col,width=width,anchor="w")
        sb = ttk.Scrollbar(listing, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        footer = tk.Frame(main,bg="#17191e"); footer.pack(fill="x",pady=(12,0))
        self.status = tk.StringVar(value="就绪。点击“自动查找”定位 MOD 目录。")
        tk.Label(footer,textvariable=self.status,bg="#17191e",fg="#9ca1ac",anchor="w").pack(side="left",fill="x",expand=True)
        self.progress = ttk.Progressbar(footer,mode="indeterminate",length=150); self.progress.pack(side="right")

    def navigate(self, key):
        for k,b in self.nav.items():
            b.configure(bg="#30343d" if k==key else "#20232a",
                        fg="#ffffff" if k==key else "#c7cad1")
        if key == "paths": self.start_search()
        elif key == "settings":
            messagebox.showinfo("设置","当前版本无需额外依赖。MOD 启用/禁用与备份功能将在后续版本加入。")
        elif key == "overview": self.status.set("总览：选择目录后会显示文件统计。")
        else: self.status.set("MOD 列表：显示所选目录中的文件和子目录。")

    def start_search(self):
        if self.worker and self.worker.is_alive(): return
        self.stop.clear()
        self.badge.configure(text="● 正在扫描",fg="#e3b15b")
        self.metric["state"].set("扫描中")
        self.status.set("正在搜索本机磁盘…"); self.progress.start(10)
        self.worker = threading.Thread(target=scan_mod_folders,
            args=(lambda m:self.events.put(("status",m)),
                  lambda p:self.events.put(("found",p)),self.stop),daemon=True)
        self.worker.start()

    def choose_dir(self):
        p = filedialog.askdirectory(title="选择 BrownDustX\\mods 文件夹")
        if p: self.set_root(p); self.status.set("已手动选择目录。")

    def set_root(self, folder):
        self.root_dir = os.path.abspath(folder)
        self.path_var.set(self.root_dir); self.side_path.configure(text=self.root_dir)
        self.load_items(); self.badge.configure(text="● 已定位",fg="#79c69b")

    @staticmethod
    def size_text(n):
        value=float(n)
        for unit in ("B","KB","MB","GB","TB"):
            if value < 1024 or unit=="TB":
                return f"{int(value)} B" if unit=="B" else f"{value:.1f} {unit}"
            value /= 1024
        return str(n)

    def load_items(self):
        self.items=[]; files=folders=0
        try:
            for p in Path(self.root_dir).iterdir():
                try:
                    if p.is_dir():
                        folders += 1
                        self.items.append({"name":p.name,"type":"文件夹","size":"—","path":str(p)})
                    elif p.is_file():
                        files += 1
                        self.items.append({"name":p.name,"type":p.suffix.lower() or "文件",
                                           "size":self.size_text(p.stat().st_size),"path":str(p)})
                except OSError: continue
        except (PermissionError,OSError) as e:
            self.status.set(f"无法读取目录：{e}")
        self.metric["total"].set(str(files+folders)); self.metric["files"].set(str(files))
        self.metric["folders"].set(str(folders)); self.metric["state"].set("已完成")
        self.render_items()
        self.status.set(f"已读取目录：{files} 个文件，{folders} 个子目录。")

    def render_items(self):
        self.tree.delete(*self.tree.get_children())
        q=self.filter_var.get().strip().casefold()
        for item in self.items:
            if q and not any(q in item[k].casefold() for k in ("name","type","path")): continue
            self.tree.insert("","end",values=(item["name"],item["type"],item["size"],item["path"]))

    def open_dir(self):
        p=self.root_dir
        if not p or not os.path.isdir(p):
            messagebox.showinfo("提示","请先自动查找或手动选择有效目录。"); return
        try:
            if os.name=="nt": os.startfile(p)
            elif sys.platform=="darwin": subprocess.Popen(["open",p])
            else: subprocess.Popen(["xdg-open",p])
        except Exception as e: messagebox.showerror("打开失败",str(e))

    def poll_events(self):
        try:
            while True:
                kind, value=self.events.get_nowait()
                if kind=="status":
                    self.status.set(value)
                    if value.startswith(("扫描完成","未找到","搜索已停止")):
                        self.progress.stop()
                        self.metric["state"].set("已完成" if value.startswith("扫描完成") else "未找到")
                        self.badge.configure(text="● 已定位" if value.startswith("扫描完成") else "● 未找到",
                                             fg="#79c69b" if value.startswith("扫描完成") else "#e3b15b")
                elif kind=="found" and value:
                    self.set_root(value[0])
                    self.status.set(f"找到 {len(value)} 个匹配目录，当前显示第一个。")
        except queue.Empty: pass
        if self.worker and not self.worker.is_alive(): self.progress.stop()
        self.after(100,self.poll_events)

if __name__ == "__main__":
    Manager().mainloop()
