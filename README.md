# MosaicView

`MosaicView` 是一个基于 `PyQt5` 的桌面图片对比工具，适合：

- 多窗口并排查看图片
- 同步缩放与同步平移
- 2 到 4 张图片的滑动叠加比较
- 拖拽加载本地图片
- 将块级 CSV 数据作为独立矢量图层叠加到鼠标指向的图片窗口
- 在图片坐标中框选位置，并将矩形标记同步到所有图片窗口

当前仓库已经整理为标准 Python 工程，可直接安装，也可模块方式运行。

## 环境要求

- `Python 3.11+`
- `PyQt5 5.15.x`
- `piexif`

## 安装

推荐用虚拟环境或 `conda` 环境：

```bash
cd /Users/halley/Project/MosaicView
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

如果你使用 `conda`：

```bash
conda create -y -n mosaic_view python=3.11 pip
conda activate mosaic_view
pip install -e .
```

## 启动方式

推荐：

```bash
python -m mosaic_view
```

安装后也可以直接用命令行入口：

```bash
mosaic-view
```

保留兼容方式：

```bash
python mosaic_view/mosaic_view.py
```

## 打包为 macOS App

当前项目已提供 PyInstaller 配置，可打包成可双击运行的 `.app`：

```bash
cd /Users/halley/Project/MosaicView
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m pip install pyinstaller
python -m PyInstaller --noconfirm ./packaging/mosaic-view-macos.spec
```

生成结果：

```text
dist/MosaicView.app
```

启动打包后的 App：

```bash
open "dist/MosaicView.app"
```

如果需要干净重打包：

```bash
rm -rf build dist
python -m PyInstaller --noconfirm packaging/mosaic-view-macos.spec
```

说明：

- macOS App 需要在 macOS 上打包。
- Apple Silicon Python 打出的包适合 Apple Silicon Mac；如需 Intel Mac 支持，需要使用 x86_64 Python 打包。
- 如果要分发给其他电脑，macOS 可能还需要代码签名和 notarization。

## 常见用法

直接启动程序：

```bash
python -m mosaic_view
```

启动时直接加载多张独立图片：

```bash
python -m mosaic_view --paths a.jpg b.jpg c.tif
```

启动时直接创建叠加视图：

```bash
python -m mosaic_view \
  --overlay_path_main_topleft base.tif \
  --overlay_path_topright ir.tif \
  --overlay_path_bottomleft xray.tif \
  --overlay_path_bottomright uv.tif
```

叠加模式规则：

- `Base + right image = left-right`
- `Base + bottom image = top-bottom`
- `3 to 4 images = quad`

块级 CSV 可视化：

- 将 `.csv` 文件直接拖到需要加载数据的目标图片窗口。
- CSV 只作用于鼠标释放位置下方的窗口，不影响其他图片窗口。
- 加载成功后，可在左侧 `CSV Overlay` 面板调整透明度、开关块边框、显示块数值、选择黑白标签或关闭 CSV。
- CSV 声明的画面尺寸必须与活动窗口主图尺寸一致。

同步矩形标记：

- 在左侧 `Rectangle Mark` 面板设置线宽、线型和颜色。
- 点击 `Start drawing` 后，在当前活动窗口中拖拽绘制矩形。
- 矩形使用图片坐标同步到所有已打开窗口，新打开的窗口也会显示已有标记。
- 在标记列表中选择目标后，点击 `Delete selected mark` 可只删除指定矩形。

## 启动参数

```bash
python -m mosaic_view --help
```

当前主要参数：

- `--hide`：启动时隐藏左右侧栏
- `--fullscreen`：启动时全屏
- `--paths`：启动时加载多张独立图片
- `--overlay_path_main_topleft`：叠加主图
- `--overlay_path_topright`：右侧图
- `--overlay_path_bottomleft`：下侧图
- `--overlay_path_bottomright`：四格模式额外图

## 当前界面结构

- 左侧：图片创建与主控制区
- 中间：干净的图像显示区域
- 右侧：`Image Stats`，显示当前活动视图中所有图片的基础信息

## 常用操作

- `F`：全屏开关
- `H`：显示或隐藏侧栏
- `Ctrl+C`：复制当前 viewer 截图
- 鼠标滚轮：缩放
- 左键拖动：平移
- 右键图像：打开高级菜单

## 项目结构

```text
MosaicView/
├── pyproject.toml
├── README.md
├── LICENSE.txt
└── mosaic_view/
    ├── __init__.py
    ├── __main__.py
    ├── mosaic_view.py
    ├── app/
    │   └── bootstrap.py
    ├── domain/
    │   └── models.py
    ├── services/
    │   ├── image_loader.py
    │   ├── metadata.py
    │   └── overlay.py
    ├── ui/
    │   ├── main_window.py
    │   ├── mdi.py
    │   ├── panels.py
    │   └── splitview.py
    ├── aux_splitview.py
    ├── aux_mdi.py
    ├── aux_interfaces.py
    ├── aux_dragdrop.py
    ├── aux_scenes.py
    ├── aux_buttons.py
    ├── aux_labels.py
    ├── aux_comments.py
    ├── aux_rulers.py
    ├── aux_dialogs.py
    ├── aux_trackers.py
    ├── aux_viewing.py
    ├── aux_functions.py
    ├── aux_exif.py
    ├── icons.qrc
    ├── icons_rc.py
    └── icons/
```

模块职责大致如下：

- `app/bootstrap.py`：CLI、`QApplication` 初始化、启动装配
- `ui/main_window.py`：主窗口与主流程控制
- `ui/splitview.py`：单图/叠加视图核心逻辑
- `ui/mdi.py`：多子窗口容器与排布
- `ui/panels.py`：左侧创建器和右侧统计面板
- `services/`：图片加载、overlay 布局、stats 元数据服务
- `domain/models.py`：轻量领域模型
- `aux_*`：兼容层和底层支撑模块，保留旧导入路径

## 当前工程说明

这次整理移除了与当前运行无关的旧工程配置：

- 旧 `installer/` 打包脚本
- 旧 `environment.yml`

仓库现在以 `pyproject.toml` 作为主工程配置，面向本地开发和标准 `pip` 安装。
