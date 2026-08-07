import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
import time
import xml.etree.ElementTree as ET

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
IO_DIR = os.path.join(CURRENT_DIR, "porter", "io")
IMAGES_DIR = os.path.join(CURRENT_DIR, "porter", "images")
MENUS_DIR = os.path.join(CURRENT_DIR, "porter", "menus")

ON_ANDROID = "ANDROID_ARGUMENT" in os.environ
ON_IOS = sys.platform == "ios" or "IOS_IS_WINDOWED" in os.environ
ON_WINDOWS = platform.system() == "Windows" and not ON_ANDROID and not ON_IOS

BUILDOZER_SPEC_PATH = os.path.join(ROOT_DIR, "buildozer.spec")
ROOT_MAIN_PATH = os.path.join(ROOT_DIR, "main.py")
WINDOWS_SPEC_PATH = os.path.join(ROOT_DIR, "mobileporter.spec")
IOS_BUILD_SCRIPT_PATH = os.path.join(ROOT_DIR, "build_ios.sh")

sys.path.insert(0, ROOT_DIR)


def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Project = load_module("Project", os.path.join(ROOT_DIR, "Project.py"))
ASTC = load_module("ASTC", os.path.join(IMAGES_DIR, "ASTC.py"))
YmlFile = load_module("YmlFile", os.path.join(IO_DIR, "YmlFile.py"))
Controls = load_module("Controls", os.path.join(IO_DIR, "Controls.py"))


def get_mobile_storage_dir():
    private_dir = os.environ.get("ANDROID_PRIVATE")
    if private_dir:
        return private_dir

    if ON_IOS:
        return os.path.join(os.path.expanduser("~"), "Documents", "mobileporter")

    return os.path.join(os.path.expanduser("~"), ".mobileporter")


class Logger:
    def __init__(self, log_file=None):
        self.steps = []
        self.log_file = log_file

    def emit(self, message):
        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as file:
                file.write(message + "\n")
        else:
            print(message)

    def step(self, name, success, detail=""):
        self.steps.append((name, success, detail))
        status = "OK" if success else "FAILED"
        self.emit(f"[{status}] {name}" + (f" — {detail}" if detail else ""))

    def summary(self):
        self.emit("\n" + "=" * 40)
        self.emit("Summary")
        self.emit("=" * 40)
        for name, success, detail in self.steps:
            status = "OK" if success else "FAILED"
            self.emit(f"{status}: {name}")


class MobilePorter:
    def __init__(self, source_path, output_path, platform_target, assets_dir,
                 convert_astc=True, generate_controls=True, generate_yml=True,
                 astcenc_path="astcenc", block_size="6x6", quality="-medium",
                 logger=None):
        self.source_path = os.path.abspath(source_path)
        self.output_path = os.path.abspath(output_path)
        self.platform_target = platform_target
        self.assets_dir = assets_dir
        self.convert_astc = convert_astc
        self.generate_controls = generate_controls
        self.generate_yml = generate_yml
        self.astcenc_path = astcenc_path
        self.block_size = block_size
        self.quality = quality
        self.project_type = None
        self.logger = logger if logger else Logger()

    def detect_project_file(self):
        hxp_path = os.path.join(self.source_path, "project.hxp")
        xml_path = os.path.join(self.source_path, "project.xml")

        if os.path.isfile(hxp_path):
            self.project_type = "hxp"
        elif os.path.isfile(xml_path):
            self.project_type = "xml"
        else:
            raise FileNotFoundError("No project.hxp or project.xml found in source project")

    def validate_source(self):
        if not os.path.isdir(self.source_path):
            raise FileNotFoundError(f"Source path not found: {self.source_path}")
        self.detect_project_file()

    def copy_project(self):
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        shutil.copytree(self.source_path, self.output_path)

    def copy_assets(self):
        source_assets = os.path.join(self.source_path, self.assets_dir)
        output_assets = os.path.join(self.output_path, self.assets_dir)

        if not os.path.isdir(source_assets):
            self.logger.step("Copy assets", False, "assets folder not found")
            return

        if os.path.exists(output_assets):
            shutil.rmtree(output_assets)

        shutil.copytree(
            source_assets,
            output_assets,
            ignore=shutil.ignore_patterns(".DS_Store", "Thumbs.db", "*.psd", "*.fla"),
        )
        self.logger.step("Copy assets", True)

    def run_astc_conversion(self):
        output_assets = os.path.join(self.output_path, self.assets_dir)

        try:
            converter = ASTC.ASTCConverter(
                output_assets, output_assets, self.block_size, self.quality, self.astcenc_path
            )
            converter.run()
            self.logger.step("ASTC conversion", True)
        except Exception as error:
            self.logger.step("ASTC conversion", False, str(error))

    def apply_platform_settings_xml(self, root):
        if self.platform_target == "android":
            self.ensure_element(root, "android", {"install-location": "auto"})
        elif self.platform_target == "ios":
            self.ensure_element(root, "ios", {"deployment-target": "12.0"})

    def ensure_element(self, root, tag, attributes):
        element = root.find(tag)
        if element is None:
            element = ET.SubElement(root, tag)
        for key, value in attributes.items():
            element.set(key, value)

    def patch_project_xml(self):
        project_xml_path = os.path.join(self.output_path, "project.xml")
        tree = ET.parse(project_xml_path)
        root = tree.getroot()

        self.apply_platform_settings_xml(root)

        tree.write(project_xml_path, encoding="utf-8", xml_declaration=True)

    def patch_project_hxp(self):
        project_hxp_path = os.path.join(self.output_path, "project.hxp")
        with open(project_hxp_path, "r", encoding="utf-8") as file:
            content = file.read()

        marker = f'// MOBILE_PORTER_TARGET: {self.platform_target}\n'
        if marker not in content:
            content = marker + content

        with open(project_hxp_path, "w", encoding="utf-8") as file:
            file.write(content)

    def patch_project_file(self):
        try:
            if self.project_type == "xml":
                self.patch_project_xml()
            elif self.project_type == "hxp":
                self.patch_project_hxp()
            self.logger.step("Patch project file", True, self.project_type)
        except Exception as error:
            self.logger.step("Patch project file", False, str(error))

    def run_controls_generation(self):
        try:
            generator = Controls.ControlsGenerator(self.output_path, Project.SOURCE_DIR)
            generator.run()
            self.logger.step("Generate mobile controls", True)
        except Exception as error:
            self.logger.step("Generate mobile controls", False, str(error))

    def run_yml_generation(self):
        yml_output = os.path.join(self.output_path, ".github", "workflows", "build.yml")
        try:
            generator = YmlFile.YmlFileGenerator(self.output_path, yml_output, Project.APP_TITLE)
            generator.write()
            self.logger.step("Generate CI YAML", True)
        except Exception as error:
            self.logger.step("Generate CI YAML", False, str(error))

    def run(self):
        start_time = time.time()

        self.validate_source()
        self.logger.step("Validate source", True, self.project_type)

        self.copy_project()
        self.logger.step("Copy project", True)

        self.copy_assets()

        if self.convert_astc:
            self.run_astc_conversion()

        self.patch_project_file()

        if self.generate_controls:
            self.run_controls_generation()

        if self.generate_yml:
            self.run_yml_generation()

        elapsed = time.time() - start_time
        self.logger.summary()
        self.logger.emit(f"\nPorted to {self.output_path} for {self.platform_target} in {elapsed:.2f}s")


def build_buildozer_spec_content():
    permissions = ",".join(Project.PERMISSIONS)
    archs = ",".join(Project.ANDROID_ARCHS)
    fullscreen_value = "1" if Project.FULLSCREEN else "0"

    return f"""[app]
title = {Project.APP_TITLE}
package.name = {Project.PACKAGE_NAME}
package.domain = {Project.PACKAGE_DOMAIN}

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = .github,.git,ports,dist,build,__pycache__,.buildozer

version = {Project.VERSION}

requirements = python3

orientation = {Project.ORIENTATION}
fullscreen = {fullscreen_value}

android.permissions = {permissions}

android.api = {Project.ANDROID_API}
android.minapi = {Project.ANDROID_MINAPI}
android.ndk = {Project.ANDROID_NDK}
android.archs = {archs}

[buildozer]
log_level = 2
warn_on_root = 1
"""


def build_root_main_content():
    return """import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(ROOT_DIR, "source")
sys.path.insert(0, SOURCE_DIR)

import Main

if __name__ == "__main__":
    Main.main()
"""


def ensure_android_spec(force=False):
    if os.path.isfile(BUILDOZER_SPEC_PATH) and not force:
        print(f"Detected existing buildozer.spec at {BUILDOZER_SPEC_PATH}")
    else:
        with open(BUILDOZER_SPEC_PATH, "w", encoding="utf-8") as file:
            file.write(build_buildozer_spec_content())
        print(f"Generated buildozer.spec at {BUILDOZER_SPEC_PATH}")

    with open(ROOT_MAIN_PATH, "w", encoding="utf-8") as file:
        file.write(build_root_main_content())
    print(f"Generated root entrypoint at {ROOT_MAIN_PATH}")


def build_windows_spec_content():
    icon_line = f"    icon='{Project.ICON_PATH}'," if Project.ICON_PATH else ""

    return f"""# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['source/Main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('Project.py', '.'), ('source', 'source')],
    hiddenimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='{Project.APP_FILE}',
    console=True,
{icon_line}
)
"""


def ensure_windows_spec(force=False):
    if os.path.isfile(WINDOWS_SPEC_PATH) and not force:
        print(f"Detected existing mobileporter.spec at {WINDOWS_SPEC_PATH}")
        return

    with open(WINDOWS_SPEC_PATH, "w", encoding="utf-8") as file:
        file.write(build_windows_spec_content())
    print(f"Generated mobileporter.spec at {WINDOWS_SPEC_PATH}")


def build_ios_script_content():
    return f"""#!/bin/bash
set -e

pip install kivy-ios

toolchain build python3 kivy

toolchain create "{Project.APP_TITLE}" "{Project.SOURCE_DIR}"

echo "Xcode project generated. Open the .xcodeproj folder to sign and build for {Project.PACKAGE}."
"""


def ensure_ios_script(force=False):
    if os.path.isfile(IOS_BUILD_SCRIPT_PATH) and not force:
        print(f"Detected existing build_ios.sh at {IOS_BUILD_SCRIPT_PATH}")
        return

    with open(IOS_BUILD_SCRIPT_PATH, "w", encoding="utf-8") as file:
        file.write(build_ios_script_content())

    os.chmod(IOS_BUILD_SCRIPT_PATH, 0o755)
    print(f"Generated build_ios.sh at {IOS_BUILD_SCRIPT_PATH}")


def parse_args():
    parser = argparse.ArgumentParser(description="Mobile-Porter: port a desktop project to mobile")
    parser.add_argument("source", nargs="?", help="Path to the source desktop project")
    parser.add_argument("output", nargs="?", help="Path to write the ported project")
    parser.add_argument("--platform", choices=["android", "ios"], help="Target mobile platform")
    parser.add_argument("--assets-dir", default=Project.ASSETS_DIR, help="Relative path to the assets folder")
    parser.add_argument("--no-astc", action="store_true", help="Skip ASTC texture conversion")
    parser.add_argument("--no-controls", action="store_true", help="Skip mobile controls generation")
    parser.add_argument("--no-yml", action="store_true", help="Skip CI YAML generation")
    parser.add_argument("--astcenc-path", default="astcenc", help="Path to the astcenc executable")
    parser.add_argument("--block-size", default="6x6", help="ASTC block size")
    parser.add_argument("--quality", default="-medium", help="astcenc quality preset")
    parser.add_argument("--prepare-android", action="store_true", help="Detect or generate buildozer.spec and root main.py, then exit")
    parser.add_argument("--prepare-windows", action="store_true", help="Detect or generate mobileporter.spec for PyInstaller, then exit")
    parser.add_argument("--prepare-ios", action="store_true", help="Detect or generate build_ios.sh for kivy-ios, then exit")
    parser.add_argument("--force-spec", action="store_true", help="Regenerate the target spec/script even if it already exists")
    return parser.parse_args()


def run_menu():
    Menu = load_module("Menu", os.path.join(MENUS_DIR, "Menu.py"))
    menu = Menu.MainMenu()
    menu.run()


def run_mobile_config(platform_name, default_platform_target):
    storage_dir = get_mobile_storage_dir()
    os.makedirs(storage_dir, exist_ok=True)

    config_path = os.path.join(storage_dir, f"{platform_name}_config.json")
    log_path = os.path.join(storage_dir, "mobileporter.log")

    logger = Logger(log_file=log_path)

    if not os.path.isfile(config_path):
        default_config = {
            "source": "",
            "output": "",
            "platform": default_platform_target,
            "assets_dir": Project.ASSETS_DIR,
            "convert_astc": True,
            "generate_controls": True,
            "generate_yml": True,
        }
        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(default_config, file, indent=4)
        logger.step("Create default config", True, config_path)
        return

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    if not config.get("source") or not config.get("output"):
        logger.step("Read config", False, f"source or output missing in {platform_name}_config.json")
        return

    porter = MobilePorter(
        config["source"],
        config["output"],
        config.get("platform", default_platform_target),
        config.get("assets_dir", Project.ASSETS_DIR),
        convert_astc=config.get("convert_astc", True),
        generate_controls=config.get("generate_controls", True),
        generate_yml=config.get("generate_yml", True),
        logger=logger,
    )

    try:
        porter.run()
    except Exception as error:
        logger.step("Run porter", False, str(error))


def run_android():
    run_mobile_config("android", "android")


def run_ios():
    run_mobile_config("ios", "ios")


def main():
    args = parse_args()

    if args.prepare_android:
        ensure_android_spec(force=args.force_spec)
        return

    if args.prepare_windows:
        ensure_windows_spec(force=args.force_spec)
        return

    if args.prepare_ios:
        ensure_ios_script(force=args.force_spec)
        return

    if ON_IOS:
        run_ios()
        return

    if ON_ANDROID:
        run_android()
        return

    if not args.source or not args.output or not args.platform:
        run_menu()
        return

    porter = MobilePorter(
        args.source,
        args.output,
        args.platform,
        args.assets_dir,
        convert_astc=not args.no_astc,
        generate_controls=not args.no_controls,
        generate_yml=not args.no_yml,
        astcenc_path=args.astcenc_path,
        block_size=args.block_size,
        quality=args.quality,
    )

    try:
        porter.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
