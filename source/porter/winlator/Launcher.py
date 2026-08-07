import ctypes
import importlib.util
import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
IO_DIR = os.path.join(ROOT_DIR, "source", "porter", "io")
IMAGES_DIR = os.path.join(ROOT_DIR, "source", "porter", "images")

EXE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(EXE_DIR, "winlator_config.json")
LOG_PATH = os.path.join(EXE_DIR, "winlator.log")

sys.path.insert(0, ROOT_DIR)


def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Project = load_module("Project", os.path.join(ROOT_DIR, "Project.py"))


def is_running_under_wine():
    try:
        ntdll = ctypes.windll.ntdll
        return hasattr(ntdll, "wine_get_version")
    except (AttributeError, OSError):
        return False


def is_running_under_winlator():
    if not is_running_under_wine():
        return False

    wineprefix = os.environ.get("WINEPREFIX", "")
    markers = ["winlator", "imagefs", "xuser"]

    return any(marker in wineprefix.lower() for marker in markers)


class Logger:
    def __init__(self, log_file):
        self.steps = []
        self.log_file = log_file

    def emit(self, message):
        with open(self.log_file, "a", encoding="utf-8") as file:
            file.write(message + "\n")

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


def load_or_create_config(logger):
    if not os.path.isfile(CONFIG_PATH):
        default_config = {
            "source": "",
            "output": "",
            "platform": "android",
            "assets_dir": Project.ASSETS_DIR,
            "convert_astc": True,
            "generate_controls": True,
            "generate_yml": True,
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as file:
            json.dump(default_config, file, indent=4)
        logger.step("Create default config", True, CONFIG_PATH)
        return None

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def run_winlator():
    logger = Logger(LOG_PATH)
    logger.step("Detect Winlator", True, f"WINEPREFIX={os.environ.get('WINEPREFIX', 'unset')}")

    config = load_or_create_config(logger)
    if config is None:
        return

    if not config.get("source") or not config.get("output"):
        logger.step("Read config", False, "source or output missing in winlator_config.json")
        return

    Main = load_module("Main", os.path.join(ROOT_DIR, "source", "Main.py"))

    porter = Main.MobilePorter(
        config["source"],
        config["output"],
        config.get("platform", "android"),
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


def run_fallback():
    print("Not running under a detected Winlator container.")
    print("Launching the normal interactive menu instead.")

    Menu = load_module("Menu", os.path.join(ROOT_DIR, "source", "porter", "menus", "Menu.py"))
    menu = Menu.MainMenu()
    menu.run()


def main():
    if is_running_under_winlator():
        run_winlator()
    else:
        run_fallback()


if __name__ == "__main__":
    main()
