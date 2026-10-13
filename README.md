# BrownDust2 MOD 管理器

一个使用 Python 标准库编写的桌面工具，帮助玩家定位《棕色尘埃2》的 BrownDustX MOD 目录，并管理 MOD 项目状态。

## 当前功能

- 深色桌面界面：总览、MOD 列表、路径查找和设置导航。
- 自动扫描本机可访问磁盘，查找目标目录；也可手动选择目录。
- 通过系统文件管理器打开 MOD 目录。
- 展示文件名、分类、大小和路径，并可按名称、类型或路径过滤。
- 自动识别常见类型：MOD 文件夹、BepInEx DLL 插件、压缩包、游戏资源、配置文件、图像/纹理及其他文件。
- 统计文件、子目录和条目总数。
- 对选中项目执行启用/禁用切换。
- GitHub Actions 自动构建 Windows 单文件 EXE，并提供构建产物下载。

目标目录结构：

```text
Neowiz\Browndust2\BrownDust2\_10000002\BepInEx\plugins\BrownDustX\mods
```

## 运行 Python 版本

需要 Python 3.10 或更新版本，无需安装第三方依赖：

```bash
python BrownDust2_MOD_Manager_Advanced.py
```

## 获取 Windows EXE

每次相关源码推送到 `main` 分支后，GitHub Actions 会自动运行构建：

1. 打开仓库的 **Actions** 页面。
2. 选择最新的 **Build Windows EXE** 工作流运行记录。
3. 在页面底部的 **Artifacts** 区域下载 `BrownDust2-MOD-Manager-Windows`。
4. 解压后运行 `BrownDust2_MOD_Manager_Advanced.exe`。

也可以在 Actions 中手动运行工作流。EXE 是构建产物，不会直接作为源码提交到仓库。

## 使用方法

1. 启动程序。
2. 点击“自动查找”扫描可访问的磁盘；大型磁盘可能需要几分钟。
3. 如果没有找到，点击“选择目录”手动指定 `BrownDustX\mods`。
4. 在列表中查看文件分类和状态，可使用过滤框搜索。
5. 选中一项后点击“启用 / 禁用所选项”，按提示确认。

## 启用/禁用说明与注意事项

启用/禁用功能通过重命名所选文件或文件夹实现：禁用时在名称末尾添加 `.disabled`，启用时移除该后缀。它不会删除文件，但会更改名称；这可能影响依赖原始名称或特定目录结构的 MOD。请先备份重要文件，并仅对你了解的项目使用该功能。

自动识别是根据文件扩展名和文件夹类型进行的启发式分类，不代表对 MOD 内容的安全审查，也不保证能识别每个 MOD 的真实名称。

## 当前限制

- 自动搜索速度取决于磁盘大小、权限和文件系统状态。
- EXE 由 GitHub Actions 构建；首次推送后请等工作流完成，再从 Artifacts 下载。
- 本工具不会主动连接游戏服务器，也不需要游戏账号或密码。
