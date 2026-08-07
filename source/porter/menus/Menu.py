import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, SOURCE_DIR)

from Main import MobilePorter


class MainMenu:
    def __init__(self):
        self.source_path = None
        self.output_base = None
        self.assets_dir = "assets"

    def print_header(self):
        print("=" * 40)
        print("Mobile-Porter")
        print("=" * 40)

    def ask_source_path(self):
        while True:
            path = input("Source project path: ").strip()
            if os.path.isdir(path):
                self.source_path = os.path.abspath(path)
                return
            print(f"Path not found: {path}")

    def ask_output_base(self):
        default_output = os.path.join(os.path.dirname(self.source_path), "ports")
        path = input(f"Output base folder [{default_output}]: ").strip()
        self.output_base = path if path else default_output

    def ask_assets_dir(self):
        path = input(f"Assets folder name [{self.assets_dir}]: ").strip()
        if path:
            self.assets_dir = path

    def port_platform(self, platform):
        output_path = os.path.join(self.output_base, platform)
        print(f"\nPorting to {platform}...")

        porter = MobilePorter(self.source_path, output_path, platform, self.assets_dir)

        try:
            porter.run()
        except Exception as error:
            print(f"Failed to port to {platform}: {error}")
            return False

        return True

    def run(self):
        self.print_header()
        self.ask_source_path()
        self.ask_output_base()
        self.ask_assets_dir()

        results = {}
        for platform in ("android", "ios"):
            results[platform] = self.port_platform(platform)

        print("\n" + "=" * 40)
        print("Summary")
        print("=" * 40)
        for platform, success in results.items():
            status = "OK" if success else "FAILED"
            print(f"{platform}: {status}")


def main():
    menu = MainMenu()
    menu.run()


if __name__ == "__main__":
    main()
