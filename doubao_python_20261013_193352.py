import sys
import os
import ctypes
import shutil
import zipfile
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES  # 拖拽依赖，需要安装 tkinterdnd2

# ==================== 配置常量 ====================
TARGET_RELATIVE_PATH = r"Neowiz\Browndust2\BrownDust2\_10000002\BepInEx\plugins\BrownDustX\mods"
MOD_JSON_NAME = "mod.json"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_windows_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drives.append(f"{letter}:\\")
        bitmask >>= 1
    return drives

# ==================== 扫描函数 ====================
def scan_mod_directory():
    found_paths = []
    drives = get_windows_drives()
    for drive in drives:
        root = Path(drive)
        try:
            for neowiz_dir in root.rglob("Neowiz"):
                candidate = neowiz_dir.parent / TARGET_RELATIVE_PATH
                if candidate.exists() and candidate.is_dir():
                    p_str = str(candidate)
                    if p_str not in found_paths:
                        found_paths.append(p_str)
        except PermissionError:
            continue
        except Exception:
            continue
    return found_paths

# ==================== 主程序类 ====================
class BD2ModManager:
    def __init__(self, root_win):
        self.root = root_win
        self.root.title("棕色尘埃2 MOD管理器")
        self.root.geometry("1000x650")
        self.current_mods_path = None
        self.mod_list = []

        # 绑定拖拽事件
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop_zip)

        # 顶部框架
        frame_top = ttk.Frame(root_win)
        frame_top.pack(fill=tk.X, padx=10, pady=5)

        self.btn_scan = ttk.Button(frame_top, text="🔍 扫描游戏MOD目录", command=self.on_scan)
        self.btn_scan.pack(side=tk.LEFT, padx=5)
        self.btn_manual_path = ttk.Button(frame_top, text="📂 手动选择MOD目录", command=self.manual_select_mods_path)
        self.btn_manual_path.pack(side=tk.LEFT, padx=5)

        ttk.Label(frame_top, text="MOD目录：").pack(side=tk.LEFT, padx=5)
        self.path_combo = ttk.Combobox(frame_top, width=55, state="readonly")
        self.path_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.path_combo.bind("<<ComboboxSelected>>", self.on_select_path)

        # 中间区域：左侧MOD列表，右侧MOD详情面板
        frame_mid = ttk.Frame(root_win)
        frame_mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧MOD列表
        list_frame = ttk.Frame(frame_mid)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(list_frame, text="MOD列表（勾选启用）").pack(anchor="w")

        self.mod_tree = ttk.Treeview(list_frame, columns=("mod_name", "status"), show="headings")
        self.mod_tree.heading("mod_name", text="MOD名称")
        self.mod_tree.heading("status", text="状态")
        self.mod_tree.column("mod_name", width=380)
        self.mod_tree.column("status", width=100)
        self.mod_tree.bind("<<TreeviewSelect>>", self.on_mod_selected)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.mod_tree.yview)
        self.mod_tree.configure(yscrollcommand=scrollbar.set)
        self.mod_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 右侧 MOD详情面板
        detail_frame = ttk.LabelFrame(frame_mid, text="MOD信息(mod.json)")
        detail_frame.pack(side=tk.RIGHT, padx=(10,0), fill=tk.BOTH)
        self.detail_text = tk.Text(detail_frame, width=30, height=15)
        self.detail_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # 底部按钮栏
        frame_bottom = ttk.Frame(root_win)
        frame_bottom.pack(fill=tk.X, padx=10, pady=8)

        self.btn_toggle = ttk.Button(frame_bottom, text="✅/❌ 切换选中MOD启用状态", command=self.toggle_selected_mod)
        self.btn_toggle.pack(side=tk.LEFT, padx=5)

        self.btn_del_dup = ttk.Button(frame_bottom, text="🗑️ 删除重复MOD", command=self.delete_duplicate_mod)
        self.btn_del_dup.pack(side=tk.LEFT, padx=5)

        self.btn_backup = ttk.Button(frame_bottom, text="💾 备份选中MOD为ZIP", command=self.backup_selected_mod)
        self.btn_backup.pack(side=tk.LEFT, padx=5)

        self.btn_refresh = ttk.Button(frame_bottom, text="🔄 刷新MOD列表", command=self.refresh_mod_list)
        self.btn_refresh.pack(side=tk.LEFT, padx=5)

        self.btn_open_folder = ttk.Button(frame_bottom, text="📂 打开MOD文件夹", command=self.open_mods_folder)
        self.btn_open_folder.pack(side=tk.RIGHT, padx=5)

        # 拖拽提示标签
        tip_label = ttk.Label(root_win, text="💡 提示：直接把MOD的ZIP压缩包拖拽进窗口自动安装MOD")
        tip_label.pack(padx=10)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(root_win, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill=tk.X, padx=10, pady=3)

    def on_scan(self):
        self.status_var.set("正在全盘扫描，请稍候...")
        self.root.update_idletasks()
        paths = scan_mod_directory()
        self.path_combo["values"] = paths
        if len(paths) > 0:
            self.path_combo.current(0)
            self.on_select_path(None)
            self.status_var.set(f"扫描完成，找到 {len(paths)} 个MOD目录")
        else:
            self.status_var.set("未找到MOD目录，请手动选择")
            messagebox.showwarning("未找到", "没有自动找到目标mods文件夹！\n可以使用【手动选择MOD目录】按钮指定。")

    def manual_select_mods_path(self):
        sel_dir = filedialog.askdirectory(title="选择BrownDustX的mods文件夹")
        if not sel_dir:
            return
        self.current_mods_path = sel_dir
        # 添加到下拉框
        all_vals = list(self.path_combo["values"])
        if sel_dir not in all_vals:
            all_vals.append(sel_dir)
            self.path_combo["values"] = all_vals
        self.path_combo.set(sel_dir)
        self.refresh_mod_list()
        self.status_var.set(f"已手动选定MOD目录：{sel_dir}")

    def on_select_path(self, event):
        selected = self.path_combo.get()
        if selected and os.path.isdir(selected):
            self.current_mods_path = selected
            self.refresh_mod_list()

    def refresh_mod_list(self):
        self.mod_tree.delete(*self.mod_tree.get_children())
        self.detail_text.delete(1.0, tk.END)
        if not self.current_mods_path or not os.path.exists(self.current_mods_path):
            return
        self.mod_list = []
        mod_dirs = [p for p in Path(self.current_mods_path).iterdir() if p.is_dir()]
        for mod_dir in mod_dirs:
            dll_files = list(mod_dir.glob("*.dll"))
            dll_disabled = list(mod_dir.glob("*.dll.disabled"))
            status = "启用" if len(dll_files) > 0 else "禁用"
            # 读取mod.json
            json_data = {}
            json_file = mod_dir / MOD_JSON_NAME
            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        json_data = json.load(f)
                except Exception:
                    json_data = {"error": "json解析失败"}

            self.mod_list.append({
                "folder": str(mod_dir),
                "name": mod_dir.name,
                "status": status,
                "dll_list": dll_files,
                "dll_disabled_list": dll_disabled,
                "json": json_data
            })
            self.mod_tree.insert("", tk.END, values=(mod_dir.name, status))
        self.status_var.set(f"已加载 {len(self.mod_list)} 个MOD")

    def on_mod_selected(self, event):
        """选中MOD时，右侧面板加载mod.json信息"""
        self.detail_text.delete(1.0, tk.END)
        sel = self.mod_tree.selection()
        if not sel:
            return
        row = self.mod_tree.item(sel[0], "values")
        mod_name = row[0]
        mod_info = next((x for x in self.mod_list if x["name"] == mod_name), None)
        if not mod_info:
            return
        j = mod_info["json"]
        if not j:
            self.detail_text.insert(tk.END, "无 mod.json 配置文件")
            return
        info_text = f"""MOD名称：{j.get('name', mod_name)}
版本：{j.get('version','未知')}
作者：{j.get('author','未知')}

描述：
{j.get('description','无描述')}
"""
        self.detail_text.insert(tk.END, info_text)

    def toggle_selected_mod(self):
        selected_items = self.mod_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先在列表选中一个MOD")
            return
        for item_id in selected_items:
            row = self.mod_tree.item(item_id, "values")
            mod_name = row[0]
            mod_info = next((x for x in self.mod_list if x["name"] == mod_name), None)
            if not mod_info:
                continue
            folder_path = Path(mod_info["folder"])
            for d in mod_info["dll_list"]:
                os.rename(d, d.with_suffix(".dll.disabled"))
            for d in mod_info["dll_disabled_list"]:
                os.rename(d, d.with_suffix(".dll"))
        self.refresh_mod_list()
        messagebox.showinfo("完成", "选中MOD状态已切换")

    def delete_duplicate_mod(self):
        if not self.current_mods_path:
            messagebox.showerror("错误", "请先选择MOD目录")
            return
        mod_path = Path(self.current_mods_path)
        all_mod_folders = [x for x in mod_path.iterdir() if x.is_dir()]
        name_map = {}
        for folder in all_mod_folders:
            lower_name = folder.name.lower()
            if lower_name not in name_map:
                name_map[lower_name] = []
            name_map[lower_name].append(folder)
        duplicates = []
        for k, v in name_map.items():
            if len(v) > 1:
                duplicates.extend(v[1:])
        if len(duplicates) == 0:
            messagebox.showinfo("结果", "未检测到重复MOD文件夹")
            return
        dup_text = "\n".join([str(x) for x in duplicates])
        ans = messagebox.askyesno("确认删除", f"检测到 {len(duplicates)} 个重复MOD文件夹\n将永久删除：\n{dup_text}\n确定删除吗？删除后无法恢复！")
        if ans:
            for f in duplicates:
                shutil.rmtree(f)
            self.refresh_mod_list()
            messagebox.showinfo("完成", f"已删除 {len(duplicates)} 个重复MOD")

    def backup_selected_mod(self):
        """备份选中MOD到zip"""
        selected_items = self.mod_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选中MOD")
            return
        row = self.mod_tree.item(selected_items[0], "values")
        mod_name = row[0]
        mod_info = next((x for x in self.mod_list if x["name"] == mod_name), None)
        if not mod_info:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP压缩包", "*.zip")],
            initialfile=f"{mod_name}_backup.zip",
            title="保存MOD备份"
        )
        if not save_path:
            return
        src_folder = Path(mod_info["folder"])
        with zipfile.ZipFile(save_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(src_folder):
                for file in files:
                    fp = Path(root)/file
                    arcname = fp.relative_to(src_folder.parent)
                    zipf.write(fp, arcname)
        self.status_var.set(f"备份完成：{save_path}")
        messagebox.showinfo("备份成功", f"MOD已备份至：{save_path}")

    def on_drop_zip(self, event):
        """拖拽zip文件进来自动解压安装MOD"""
        file_paths = self.root.tk.splitlist(event.data)
        if not self.current_mods_path:
            messagebox.showerror("错误", "请先选定MOD目录！")
            return
        for fpath in file_paths:
            p = Path(fpath)
            if not p.suffix.lower() == ".zip":
                messagebox.showwarning("跳过", f"{p.name} 不是zip压缩包，跳过")
                continue
            try:
                # 读取压缩包内顶层目录
                with zipfile.ZipFile(p, 'r') as zip_ref:
                    top_dirs = set()
                    for name in zip_ref.namelist():
                        top = name.split("/")[0]
                        top_dirs.add(top)
                    if len(top_dirs) !=1:
                        ans = messagebox.askyesno("警告", "压缩包根目录存在多个文件夹/文件\n是否继续解压？")
                        if not ans:
                            continue
                        target_dir = Path(self.current_mods_path)/p.stem
                    else:
                        target_dir = Path(self.current_mods_path)/list(top_dirs)[0]
                    if target_dir.exists():
                        overwrite = messagebox.askyesno("MOD已存在", f"{target_dir.name} 已存在，是否覆盖？")
                        if not overwrite:
                            continue
                        shutil.rmtree(target_dir)
                    zip_ref.extractall(Path(self.current_mods_path))
                self.refresh_mod_list()
                self.status_var.set(f"{p.name} 导入完成")
            except Exception as e:
                messagebox.showerror("解压失败", f"{p.name} 解压出错：{str(e)}")

    def open_mods_folder(self):
        if self.current_mods_path and os.path.isdir(self.current_mods_path):
            os.startfile(self.current_mods_path)
        else:
            messagebox.showerror("错误", "MOD目录不存在")

if __name__ == "__main__":
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    else:
        root = TkinterDnD.Tk()
        app = BD2ModManager(root)
        root.mainloop()
#（注：内容由AI生成）
