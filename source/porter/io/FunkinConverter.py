import argparse
import json
import os
import re
import shutil
import sys


MODULE_HXC_TEMPLATE = """package;

import funkin.modding.module.Module;

class {class_name} extends Module
{{
	public function new()
	{{
		super("{mod_id}", 0);
	}}

	override function onCreate():Void
	{{
		super.onCreate();
	}}
}}
"""


def to_pascal_case(mod_id):
    parts = re.split(r"[-_\s]+", mod_id.strip())
    return "".join(part[:1].upper() + part[1:] for part in parts if part)


class FunkinConverterGenerator:
    def __init__(self, output_path, mod_id, mod_name, mod_description="", mod_homepage="",
                 api_version="1.0.0", legacy_lua_path=None):
        self.output_path = os.path.abspath(output_path)
        self.mod_id = mod_id
        self.mod_name = mod_name
        self.mod_description = mod_description
        self.mod_homepage = mod_homepage
        self.api_version = api_version
        self.legacy_lua_path = os.path.abspath(legacy_lua_path) if legacy_lua_path else None
        self.class_name = to_pascal_case(mod_id) or "MyMod"

        self.mods_dir = os.path.join(self.output_path, "mods")
        self.mod_dir = os.path.join(self.mods_dir, self.mod_id)
        self.assets_dir = os.path.join(self.mod_dir, "assets")
        self.scripts_dir = os.path.join(self.mod_dir, "scripts")

    def validate_output(self):
        if not os.path.isdir(self.output_path):
            raise FileNotFoundError(f"Funkin' checkout not found: {self.output_path}")

    def build_meta_json(self):
        return {
            "id": self.mod_id,
            "name": self.mod_name,
            "description": self.mod_description,
            "homepage": self.mod_homepage,
            "license": "Unspecified",
            "api_version": self.api_version,
            "mod_version": "1.0.0",
        }

    def write_meta(self):
        os.makedirs(self.mod_dir, exist_ok=True)
        meta_path = os.path.join(self.mod_dir, "_polymod_meta.json")

        with open(meta_path, "w", encoding="utf-8") as file:
            json.dump(self.build_meta_json(), file, indent=4)

        print(f"Created {meta_path}")

    def write_module_stub(self):
        os.makedirs(self.mod_dir, exist_ok=True)
        module_path = os.path.join(self.mod_dir, f"{self.class_name}.hxc")

        content = MODULE_HXC_TEMPLATE.format(class_name=self.class_name, mod_id=self.mod_id)

        with open(module_path, "w", encoding="utf-8") as file:
            file.write(content)

        print(f"Created {module_path}")

    def scaffold_folders(self):
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.scripts_dir, exist_ok=True)
        print(f"Created {self.assets_dir}")
        print(f"Created {self.scripts_dir}")

    def import_legacy_lua(self):
        if not self.legacy_lua_path:
            return

        if not os.path.isdir(self.legacy_lua_path):
            print(f"Warning: legacy Lua path not found, skipping import: {self.legacy_lua_path}")
            return

        imported_count = 0

        for root, _, files in os.walk(self.legacy_lua_path):
            for file_name in files:
                if not file_name.lower().endswith(".lua"):
                    continue

                source_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(source_path, self.legacy_lua_path)
                dest_name = os.path.splitext(relative_path)[0] + ".TODO.lua"
                dest_path = os.path.join(self.scripts_dir, dest_name)

                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copyfile(source_path, dest_path)
                imported_count += 1

        print(f"Imported {imported_count} Lua script(s) into {self.scripts_dir} (marked .TODO.lua, needs manual porting to .hxc)")

    def run(self):
        self.validate_output()
        self.scaffold_folders()
        self.write_meta()
        self.write_module_stub()
        self.import_legacy_lua()

        print(f"\nV-Slice mod scaffold ready at {self.mod_dir}")
        print(f"{self.class_name}.hxc extends Module with a confirmed onCreate() override — other real hooks exist too (e.g. onStateChangeEnd(event:StateChangeScriptEvent)), add them as needed.")
        print("Next steps: manually port each .TODO.lua script into a .hxc file extending the matching V-Slice class (Module, Song, NoteStyle, etc).")


def parse_args():
    parser = argparse.ArgumentParser(description="Scaffold a V-Slice Polymod mod from a legacy Lua-based mod")
    parser.add_argument("output", help="Path to the local FunkinCrew/Funkin checkout")
    parser.add_argument("mod_id", help="Mod folder id (lowercase, no spaces, e.g. my-mod)")
    parser.add_argument("--mod-name", help="Display name of the mod (default: mod_id)")
    parser.add_argument("--description", default="", help="Mod description")
    parser.add_argument("--homepage", default="", help="Mod homepage/repo URL")
    parser.add_argument("--api-version", default="1.0.0", help="Polymod api_version to target")
    parser.add_argument("--legacy-lua", help="Path to a folder of existing .lua scripts to import as a starting point")
    return parser.parse_args()


def main():
    args = parse_args()
    mod_name = args.mod_name if args.mod_name else args.mod_id

    generator = FunkinConverterGenerator(
        args.output, args.mod_id, mod_name, args.description, args.homepage,
        args.api_version, args.legacy_lua,
    )

    try:
        generator.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
