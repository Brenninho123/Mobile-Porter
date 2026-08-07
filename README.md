# Mobile-Porter

An automatic port generator that converts desktop Haxe/OpenFL/Lime projects into mobile-ready Android and iOS builds.

## Features

- Detects `project.xml` (OpenFL/Lime) or `project.hxp` (hxp build system) automatically
- Copies and patches the project structure for the target platform
- Ports the assets folder, ignoring working files like `.psd` and `.fla`
- Converts PNG textures to ASTC format for optimized mobile rendering
- Interactive menu to port a project to both Android and iOS in one run

## Project Structure

```
source/
  Main.py                  Entry point (CLI or interactive menu)
  porter/
    menus/
      Menu.py               Interactive menu for choosing a project and porting it
    images/
      ASTC.py               PNG to ASTC texture converter
```

## Usage

### Interactive Menu

Run without arguments to launch the menu:

```
python source/Main.py
```

You will be prompted for the source project path, an output folder, and the assets folder name. The tool then ports the project to both Android and iOS automatically.

### Direct CLI

```
python source/Main.py <source> <output> --platform android
python source/Main.py <source> <output> --platform ios
```

Optional flags:

- `--assets-dir` — relative path to the assets folder (default: `assets`)

### ASTC Conversion

Convert PNG assets to ASTC separately:

```
python source/porter/images/ASTC.py <input> <output> --block-size 6x6 --quality -medium
```

Requires [astcenc](https://github.com/ARM-software/astc-encoder) installed and available on your PATH, or pass a custom path with `--astcenc-path`.

## Requirements

- Python 3.8+
- astcenc (for texture conversion)

## License

Apache-2.0
