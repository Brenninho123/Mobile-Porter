import argparse
import os
import sys


class MainCodenameConverter:
    def __init__(self, main_hx_path):
        self.main_hx_path = os.path.abspath(main_hx_path)

    def validate(self):
        if not os.path.isfile(self.main_hx_path):
            raise FileNotFoundError(f"Main.hx not found: {self.main_hx_path}")

        with open(self.main_hx_path, "r", encoding="utf-8") as file:
            content = file.read()

        if "class Main extends Sprite" not in content:
            print("Warning: this doesn't look like CodenameEngine's Main.hx (class signature not found)")

        return content

    def patch_import(self, content):
        if "mobileporter.StorageUtil" in content:
            return content, False

        anchor = "import sys.io.File;\n#if android"
        if anchor not in content:
            print("Warning: import anchor not found, skipping StorageUtil import")
            return content, False

        replacement = "import sys.io.File;\n#if mobile\nimport mobileporter.StorageUtil;\n#end\n#if android"
        return content.replace(anchor, replacement, 1), True

    def patch_storage_init(self, content):
        if "StorageUtil.init();" in content:
            return content, False

        anchor = "Options.load();"
        if anchor not in content:
            print("Warning: Options.load() anchor not found, skipping StorageUtil.init()")
            return content, False

        replacement = "Options.load();\n\n\t\t#if mobile\n\t\tStorageUtil.init();\n\t\t#end"
        return content.replace(anchor, replacement, 1), True

    def patch_focus_lost(self, content):
        if "onFocusLost" in content:
            return content, False

        signal_anchor = "FlxG.signals.focusGained.add(onFocus);"
        if signal_anchor not in content:
            print("Warning: focusGained signal anchor not found, skipping focusLost handling")
            return content, False

        signal_replacement = "FlxG.signals.focusGained.add(onFocus);\n\t\t#if mobile\n\t\tFlxG.signals.focusLost.add(onFocusLost);\n\t\t#end"
        content = content.replace(signal_anchor, signal_replacement, 1)

        method_anchor = "public static function onFocus() {\n\t\t_tickFocused = FlxG.game.ticks;\n\t}"
        if method_anchor not in content:
            print("Warning: onFocus() method anchor not found, skipping onFocusLost() definition")
            return content, True

        method_replacement = (
            method_anchor
            + "\n\n\t#if mobile\n\tpublic static function onFocusLost() {\n\t\tFlxG.sound.music?.pause();\n\t}\n\t#end"
        )
        content = content.replace(method_anchor, method_replacement, 1)

        return content, True

    def patch(self):
        content = self.validate()
        changes = []

        content, changed = self.patch_import(content)
        if changed:
            changes.append("import")

        content, changed = self.patch_storage_init(content)
        if changed:
            changes.append("StorageUtil.init()")

        content, changed = self.patch_focus_lost(content)
        if changed:
            changes.append("focusLost handler")

        if not changes:
            print(f"{self.main_hx_path} already has all mobile patches, nothing to do")
            return

        with open(self.main_hx_path, "w", encoding="utf-8") as file:
            file.write(content)

        print(f"Patched {self.main_hx_path}: {', '.join(changes)}")


def parse_args():
    parser = argparse.ArgumentParser(description="Patch CodenameEngine's Main.hx with mobile tooling hooks")
    parser.add_argument("main_hx", help="Path to CodenameEngine's source/funkin/backend/system/Main.hx")
    return parser.parse_args()


def main():
    args = parse_args()
    converter = MainCodenameConverter(args.main_hx)

    try:
        converter.patch()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
