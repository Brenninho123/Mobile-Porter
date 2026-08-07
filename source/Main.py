import argparse
import os
import shutil
import sys
import xml.etree.ElementTree as ET


class MobilePorter:
    def __init__(self, source_path, output_path, platform):
        self.source_path = os.path.abspath(source_path)
        self.output_path = os.path.abspath(output_path)
        self.platform = platform

    def validate_source(self):
        if not os.path.isdir(self.source_path):
            raise FileNotFoundError(f"Source path not found: {self.source_path}")

        project_xml = os.path.join(self.source_path, "project.xml")
        if not os.path.isfile(project_xml):
            raise FileNotFoundError("project.xml not found in source project")

        return project_xml

    def copy_project(self):
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        shutil.copytree(self.source_path, self.output_path)

    def patch_project_xml(self):
        project_xml_path = os.path.join(self.output_path, "project.xml")
        tree = ET.parse(project_xml_path)
        root = tree.getroot()

        self.apply_platform_settings(root)

        tree.write(project_xml_path, encoding="utf-8", xml_declaration=True)

    def apply_platform_settings(self, root):
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

    def run(self):
        self.validate_source()
        self.copy_project()
        self.patch_project_xml()
        print(f"Ported project to {self.output_path} for platform: {self.platform}")


def parse_args():
    parser = argparse.ArgumentParser(description="Mobile-Porter: port a desktop project to mobile")
    parser.add_argument("source", help="Path to the source desktop project")
    parser.add_argument("output", help="Path to write the ported project")
    parser.add_argument("--platform", choices=["android", "ios"], required=True, help="Target mobile platform")
    return parser.parse_args()


def main():
    args = parse_args()
    porter = MobilePorter(args.source, args.output, args.platform)

    try:
        porter.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
