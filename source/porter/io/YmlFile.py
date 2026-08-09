import argparse
import os
import sys


class YmlFileGenerator:
    def __init__(self, source_path, output_path, app_title):
        self.source_path = os.path.abspath(source_path)
        self.output_path = os.path.abspath(output_path)
        self.app_title = app_title
        self.project_type = None
        self.uses_hmm = False

    def detect_project_type(self):
        hxp_path = os.path.join(self.source_path, "project.hxp")
        xml_path = os.path.join(self.source_path, "project.xml")

        if os.path.isfile(hxp_path):
            self.project_type = "hxp"
        elif os.path.isfile(xml_path):
            self.project_type = "xml"
        else:
            raise FileNotFoundError("No project.hxp or project.xml found in source project")

        self.uses_hmm = os.path.isfile(os.path.join(self.source_path, "hmm.json"))

    def build_command(self, platform):
        if self.project_type == "hxp":
            return f"haxe --run project.hxp build {platform}"
        return f"lime build {platform}"

    def build_dependency_steps(self, platform):
        if self.uses_hmm:
            return [
                "haxelib install hmm --quiet",
                "haxelib run hmm install",
            ]

        return [
            "haxelib install lime --quiet",
            "haxelib install openfl --quiet",
            f"haxelib run lime setup {platform} --quiet",
        ]

    def output_glob(self, platform):
        if platform == "android":
            return "export/release/android/bin/*.apk"
        return "export/release/ios/**"

    def cache_key_files(self):
        if self.uses_hmm:
            return "hmm.json"
        return "project.xml', 'project.hxp"

    def generate_job(self, platform, runs_on):
        command = self.build_command(platform)
        dependency_steps = "\n".join(f"          {step}" for step in self.build_dependency_steps(platform))
        artifact_name = f"{self.app_title.replace(' ', '-')}-{platform}"
        output_glob = self.output_glob(platform)
        cache_key_files = self.cache_key_files()

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

      - name: Cache haxelib
        uses: actions/cache@v4
        with:
          path: ~/.haxelib
          key: haxelib-${{{{ runner.os }}}}-${{{{ hashFiles('{cache_key_files}') }}}}
          restore-keys: |
            haxelib-${{{{ runner.os }}}}-

      - name: Install dependencies
        run: |
{dependency_steps}

      - name: Build {platform}
        run: {command}

      - name: Verify build output
        run: |
          if [ -z "$(find export/release/{platform} -type f 2>/dev/null)" ]; then
            echo "Build failed: no output found in export/release/{platform}"
            exit 1
          fi

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: {artifact_name}
          path: {output_glob}
          if-no-files-found: error
          retention-days: 30
"""

    def generate(self):
        self.detect_project_type()

        android_job = self.generate_job("android", "ubuntu-22.04")
        ios_job = self.generate_job("ios", "macos-14")

        return f"""name: Build {self.app_title}

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: ${{{{ github.workflow }}}}-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
{android_job}
{ios_job}"""

    def write(self):
        content = self.generate()
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        with open(self.output_path, "w", encoding="utf-8") as file:
            file.write(content)

        dep_mode = "hmm" if self.uses_hmm else "haxelib"
        print(f"Generated {self.output_path} ({self.project_type} project, deps via {dep_mode})")


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
