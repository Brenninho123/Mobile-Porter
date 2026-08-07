import argparse
import os
import shutil
import sys
import xml.etree.ElementTree as ET


class MobilePorter:
    def __init__(self, source_path, output_path, platform, assets_dir):
        self.source_path = os.path.abspath(source_path)
        self.output_path = os.path.abspath(output_path)
        self.platform = platform
        self.assets_dir = assets_dir
        self.project_type = None

    def detect_project_file(self):
        hxp_path = os.path.join(self.source_path, "project.hxp")
        xml_path = os.path.join(self.source_path, "project.xml")

        if os.path.isfile(hxp_path):
            self.project_type = "hxp"
            return hxp_path
        elif os.path.isfile(xml_path):
            self.project_type = "xml"
            return xml_path
        else:
            raise FileNotFoundError("No project.hxp or project.xml found in source project")

    def validate_source(self):
        if not os.path.isdir(self.source_path):
            raise FileNotFoundError(f"Source path not found: {self.source_path}")
        return self.detect_project_file()

    def copy_project(self):
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        shutil.copytree(self.source_path, self.output_path)

    def copy_assets(self):
        source_assets = os.path.join(self.source_path, self.assets_dir)
        output_assets = os.path.join(self.output_path, self.assets_dir)

        if not os.path.isdir(source_assets):
            print(f"Warning: assets folder not found at {source_assets}")
            return

        if os.path.exists(output_assets):
            shutil.rmtree(output_assets)

        shutil.copytree(
            source_assets,
            output_assets,
            ignore=shutil.ignore_patterns(".DS_Store", "Thumbs.db", "*.psd", "*.fla"),
        )

    def patch_project_xml(self):
        project_xml_path = os.path.join(self.output_path, "project.xml")
        tree = ET.parse(project_xml_path)
        root = tree.getroot()

        self.apply_platform_settings_xml(root)

        tree.write(project_xml_path, encoding="utf-8", xml_declaration=True)

    def apply_platform_settings_xml(self, root):
        if self.platform == "android":
            self.ensure_element(root, "android", {"install-location": "auto"})
        elif self.platform == "ios":
            self.ensure_element(root, "ios", {"deployment-target": "12.0"})

    def ensure_element(self, root, tag, attributes):
        element = root.find(tag)
        if element is None:
            element = ET.SubElement(root, tag)
        for key, value in attributes.items():
            element.set(key, value)

    def patch_project_hxp(self):
        project_hxp_path = os.path.join(self.output_path, "project.hxp")
        with open(project_hxp_path, "r", encoding="utf-8") as file:
            content = file.read()

        marker = f'// MOBILE_PORTER_TARGET: {self.platform}\n'
        if marker not in content:
            content = marker + content

        with open(project_hxp_path, "w", encoding="utf-8") as file:
            file.write(content)

    def run(self):
        self.validate_source()
        self.copy_project()
        self.copy_assets()

        if self.project_type == "xml":
            self.patch_project_xml()
        elif self.project_type == "hxp":
            self.patch_project_hxp()

        print(f"Ported project to {self.output_path} for platform: {self.platform} ({self.project_type})")


def parse_args():
    parser = argparse.ArgumentParser(description="Mobile-Porter: port a desktop project to mobile")
    parser.add_argument("source", nargs="?", help="Path to the source desktop project")
    parser.add_argument("output", nargs="?", help="Path to write the ported project")
    parser.add_argument("--platform", choices=["android", "ios"], help="Target mobile platform")
    parser.add_argument("--assets-dir", default="assets", help="Relative path to the assets folder")
    return parser.parse_args()


def run_menu():
    from porter.menus.Menu import MainMenu
    menu = MainMenu()
    menu.run()


def main():
    args = parse_args()

    if not args.source or not args.output or not args.platform:
        run_menu()
        return

    porter = MobilePorter(args.source, args.output, args.platform, args.assets_dir)

    try:
        porter.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
