import argparse
import os
import sys


MARKER = "Mobile-Porter Additions"

DEFAULT_PERMISSIONS = [
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.INTERNET",
    "android.permission.VIBRATE",
]


class ProjectCodenameConverter:
    def __init__(self, project_xml_path, permissions=None, ios_deployment_target="12.0"):
        self.project_xml_path = os.path.abspath(project_xml_path)
        self.permissions = permissions if permissions else DEFAULT_PERMISSIONS
        self.ios_deployment_target = ios_deployment_target

    def validate(self):
        if not os.path.isfile(self.project_xml_path):
            raise FileNotFoundError(f"project.xml not found: {self.project_xml_path}")

        with open(self.project_xml_path, "r", encoding="utf-8") as file:
            content = file.read()

        if "funkin.backend.system.Main" not in content:
            print("Warning: this doesn't look like a CodenameEngine project.xml (main class not found)")

        return content

    def already_patched(self, content):
        return MARKER in content

    def build_mobile_block(self):
        permission_lines = "\n".join(f'\t<android permission="{permission}" />' for permission in self.permissions)

        return f"""
	<!-- _________________________________ {MARKER} _______________________________ -->

	<android install-location="auto" />
{permission_lines}

	<ios deployment-target="{self.ios_deployment_target}" />
"""

    def patch(self, force=False):
        content = self.validate()

        if self.already_patched(content) and not force:
            print(f"{self.project_xml_path} is already patched, skipping (use --force to reapply)")
            return

        if force and self.already_patched(content):
            content = self.strip_existing_block(content)

        closing_tag = "</project>"
        insert_index = content.rfind(closing_tag)

        if insert_index == -1:
            raise ValueError("Could not find </project> closing tag")

        mobile_block = self.build_mobile_block()
        patched_content = content[:insert_index] + mobile_block + "\n" + content[insert_index:]

        with open(self.project_xml_path, "w", encoding="utf-8") as file:
            file.write(patched_content)

        print(f"Patched {self.project_xml_path} with mobile Android/iOS settings")

    def strip_existing_block(self, content):
        start_marker = f"<!-- _________________________________ {MARKER} _______________________________ -->"
        start_index = content.find(start_marker)

        if start_index == -1:
            return content

        block_start = content.rfind("\n", 0, start_index)
        closing_tag_index = content.find("</project>", start_index)

        if closing_tag_index == -1:
            return content

        return content[:block_start] + content[closing_tag_index:]


def parse_args():
    parser = argparse.ArgumentParser(description="Patch a CodenameEngine project.xml with mobile settings")
    parser.add_argument("project_xml", help="Path to CodenameEngine's project.xml")
    parser.add_argument("--permission", action="append", dest="permissions", help="Add an extra Android permission (repeatable)")
    parser.add_argument("--ios-deployment-target", default="12.0", help="iOS minimum deployment target")
    parser.add_argument("--force", action="store_true", help="Reapply even if already patched")
    return parser.parse_args()


def main():
    args = parse_args()
    permissions = DEFAULT_PERMISSIONS + args.permissions if args.permissions else None
    converter = ProjectCodenameConverter(args.project_xml, permissions, args.ios_deployment_target)

    try:
        converter.patch(force=args.force)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
