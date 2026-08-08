import importlib.util
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
MOBILE_DIR = os.path.join(SOURCE_DIR, "porter", "mobile")
sys.path.insert(0, SOURCE_DIR)


def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Main = load_module("Main", os.path.join(SOURCE_DIR, "Main.py"))
Battery = load_module("Battery", os.path.join(MOBILE_DIR, "Battery.py"))


class MainMenu:
    def __init__(self):
        self.source_path = None
        self.output_base = None
        self.assets_dir = "assets"
        self.convert_astc = True
        self.generate_controls = True
        self.generate_yml = True

    def print_header(self):
        print("=" * 40)
        print(f"{Main.Project.APP_TITLE} v{Main.Project.VERSION}")
        print("=" * 40)

    def print_battery_status(self):
        status = Battery.get_battery_status()

        if status is None:
            return

        charging_label = "charging" if status["charging"] else "not charging"
        print(f"Battery: {status['level']}% ({charging_label})")

        if not status["charging"] and status["level"] <= 20:
            print("Low battery detected — conversions will run slower to save power.\n")
        else:
            print("")

    def ask_yes_no(self, prompt, default=True):
        suffix = "[Y/n]" if default else "[y/N]"
        answer = input(f"{prompt} {suffix}: ").strip().lower()

        if not answer:
            return default

        return answer in ("y", "yes")

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

    def ask_pipeline_options(self):
        self.convert_astc = self.ask_yes_no("Convert PNG assets to ASTC?", default=True)
        self.generate_controls = self.ask_yes_no("Generate mobile touch controls?", default=True)
        self.generate_yml = self.ask_yes_no("Generate CI YAML for the ported project?", default=True)

    def port_platform(self, platform_target):
        output_path = os.path.join(self.output_base, platform_target)
        print(f"\nPorting to {platform_target}...")

        porter = Main.MobilePorter(
            self.source_path,
            output_path,
            platform_target,
            self.assets_dir,
            convert_astc=self.convert_astc,
            generate_controls=self.generate_controls,
            generate_yml=self.generate_yml,
        )

        try:
            porter.run()
        except Exception as error:
            print(f"Failed to port to {platform_target}: {error}")
            return False

        return True

    def run(self):
        self.print_header()
        self.print_battery_status()
        self.ask_source_path()
        self.ask_output_base()
        self.ask_assets_dir()
        self.ask_pipeline_options()

        results = {}
        for platform_target in ("android", "ios"):
            results[platform_target] = self.port_platform(platform_target)

        print("\n" + "=" * 40)
        print("Summary")
        print("=" * 40)
        for platform_target, success in results.items():
            status = "OK" if success else "FAILED"
            print(f"{platform_target}: {status}")


def main():
    menu = MainMenu()
    menu.run()


if __name__ == "__main__":
    main()
