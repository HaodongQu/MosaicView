# Packaging MosaicView

## macOS `.app`

Create a clean environment and install the project:

```bash
cd /Users/halley/Project/MosaicView
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m pip install pyinstaller
```

Build the app bundle:

```bash
python -m PyInstaller --noconfirm packaging/mosaic-view-macos.spec
```

The runnable app will be created at:

```text
dist/MosaicView.app
```

You can launch it from Finder, or from the terminal:

```bash
open "dist/MosaicView.app"
```

## Rebuild

If you need a clean rebuild:

```bash
rm -rf build dist
python -m PyInstaller --noconfirm packaging/mosaic-view-macos.spec
```

## Notes

- Build on the same platform you want to distribute. Build macOS apps on macOS, Windows `.exe` files on Windows.
- On Apple Silicon, an app built with an arm64 Python runs on Apple Silicon Macs. Use an x86_64 Python if you need Intel Mac support.
- For sharing outside your own machine, macOS may require code signing and notarization.
