import argparse
import os
import sys


class YmlFileGenerator:
    def __init__(self, source_path, output_path, app_title):
        self.source_path = os.path.abspath(source_path)
        self.output_path = os.path.abspath(output_path)
        self.app_title = app_title
        self.project_type = None

    def detect_project_type(self):
        hxp_path = os.path.join(self.source_path, "project.hxp")
        xml_path = os.path.join(self.source_path, "project.xml")

        if os.path.isfile(hxp_path):
            self.project_type = "hxp"
        elif os.path.isfile(xml_path):
            self.project_type = "xml"
        else:
            raise FileNotFoundError("No project.hxp or project.xml found in source project")

    def build_commands(self, platform):
        if self.project_type == "hxp":
            return [
                "haxe --run project.hxp build " + platform,
            ]
        else:
            return [
                f"lime build {platform}",
            ]

    def generate_job(self, platform, runs_on):
        commands = self.build_commands(platform)
        steps = "\n".join(f"        run: {command}" for command in commands)

        return f"""  build-{platform}:
    name: Build {platform.capitalize()}
    runs-on: {runs_on}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Haxe
        uses: krdlab/setup-haxe@v1
        with:
          haxe-version: 4.3.4

      - name: Install dependencies
        run: |
          haxelib install lime --quiet
          haxelib install openfl --quiet
          haxelib run lime setup {platform} --quiet

      - name: Build {platform}
{steps}

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: {self.app_title.replace(" ", "-")}-{platform}
          path: export/release/{platform}
"""

    def generate(self):
        self.detect_project_type()

        android_job = self.generate_job("android", "ubuntu-latest")
        ios_job = self.generate_job("ios", "macos-latest")

        content = f"""name: Build {self.app_title}

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
{android_job}
{ios_job}"""

        return content

    def write(self):
        content = self.generate()
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        with open(self.output_path, "w", encoding="utf-8") as file:
            file.write(content)

        print(f"Generated {self.output_path} ({self.project_type} project)")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a GitHub Actions YAML with Android and iOS build jobs")
    parser.add_argument("source", help="Path to the source desktop project")
    parser.add_argument("--output", default=".github/workflows/build.yml", help="Output path for the YAML file")
    parser.add_argument("--app-title", default="App", help="App title used in artifact names")
    return parser.parse_args()


def main():
    args = parse_args()
    generator = YmlFileGenerator(args.source, args.output, args.app_title)

    try:
        generator.write()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
