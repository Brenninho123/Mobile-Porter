import argparse
import importlib.util
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CODENAME_DIR = os.path.join(CURRENT_DIR, "codename")


def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ProjectCodename = load_module("ProjectCodename", os.path.join(CODENAME_DIR, "ProjectCodename.py"))
MainCodename = load_module("MainCodename", os.path.join(CODENAME_DIR, "MainCodename.py"))


HITBOX_HX = """package mobileporter;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup;
import flixel.math.FlxPoint;

class Hitbox extends FlxGroup
{
	public static var directions:Array<String> = ["left", "down", "up", "right"];

	var zones:Map<String, FlxSprite> = new Map();
	var pressedState:Map<String, Bool> = new Map();
	var justPressedState:Map<String, Bool> = new Map();
	var justReleasedState:Map<String, Bool> = new Map();
	var wasPressedState:Map<String, Bool> = new Map();

	public function new(visible:Bool = false, alpha:Float = 0.0)
	{
		super();

		var screenW = FlxG.width;
		var zoneW = screenW / directions.length;
		var zoneH = FlxG.height * 0.35;
		var zoneY = FlxG.height - zoneH;

		for (i in 0...directions.length)
		{
			var direction = directions[i];
			var zone = new FlxSprite(zoneW * i, zoneY);
			zone.makeGraphic(Std.int(zoneW), Std.int(zoneH), 0xFFFFFFFF);
			zone.scrollFactor.set();
			zone.alpha = alpha;
			zone.visible = visible;

			zones.set(direction, zone);
			pressedState.set(direction, false);
			justPressedState.set(direction, false);
			justReleasedState.set(direction, false);
			wasPressedState.set(direction, false);

			add(zone);
		}
	}

	override public function update(elapsed:Float):Void
	{
		super.update(elapsed);

		for (direction in directions)
		{
			var zone = zones.get(direction);
			var isPressed = false;

			for (touch in FlxG.touches.list)
			{
				if (zone.overlapsPoint(FlxPoint.get(touch.x, touch.y)))
				{
					isPressed = true;
					break;
				}
			}

			var wasPressed = wasPressedState.get(direction);

			pressedState.set(direction, isPressed);
			justPressedState.set(direction, isPressed && !wasPressed);
			justReleasedState.set(direction, !isPressed && wasPressed);
			wasPressedState.set(direction, isPressed);
		}
	}

	public function pressed(direction:String):Bool
	{
		return pressedState.get(direction) == true;
	}

	public function justPressed(direction:String):Bool
	{
		return justPressedState.get(direction) == true;
	}

	public function justReleased(direction:String):Bool
	{
		return justReleasedState.get(direction) == true;
	}

	public function anyJustPressed():Bool
	{
		for (direction in directions)
			if (justPressed(direction))
				return true;
		return false;
	}

	public function setVisible(value:Bool):Void
	{
		for (zone in zones)
			zone.visible = value;
	}

	public function setAlpha(value:Float):Void
	{
		for (zone in zones)
			zone.alpha = value;
	}
}
"""

STORAGE_UTIL_HX = """package mobileporter;

import openfl.net.SharedObject;
import haxe.Json;

class StorageUtil
{
	static var storage:SharedObject;
	static var namespace:String;

	public static function init(namespace:String = "mobileporter_data"):Void
	{
		StorageUtil.namespace = namespace;
		storage = SharedObject.getLocal(namespace);
	}

	public static function setValue(key:String, value:Dynamic):Void
	{
		ensureInit();
		Reflect.setField(storage.data, key, value);
		storage.flush();
	}

	public static function getValue(key:String, defaultValue:Dynamic = null):Dynamic
	{
		ensureInit();

		if (Reflect.hasField(storage.data, key))
			return Reflect.field(storage.data, key);

		return defaultValue;
	}

	public static function setObject(key:String, value:Dynamic):Void
	{
		setValue(key, Json.stringify(value));
	}

	public static function getObject(key:String, defaultValue:Dynamic = null):Dynamic
	{
		var raw = getValue(key, null);

		if (raw == null)
			return defaultValue;

		try
		{
			return Json.parse(raw);
		}
		catch (error:Dynamic)
		{
			return defaultValue;
		}
	}

	public static function remove(key:String):Void
	{
		ensureInit();
		Reflect.deleteField(storage.data, key);
		storage.flush();
	}

	public static function clear():Void
	{
		ensureInit();
		storage.clear();
	}

	static function ensureInit():Void
	{
		if (storage == null)
			init();
	}
}
"""


class CodenameConverterGenerator:
    def __init__(self, output_path, source_dir="source", main_hx_relative=None, patch_project=True, patch_main=True):
        self.output_path = os.path.abspath(output_path)
        self.source_dir = source_dir
        self.target_dir = os.path.join(self.output_path, self.source_dir, "mobileporter")
        self.project_xml_path = os.path.join(self.output_path, "project.xml")
        self.main_hx_relative = main_hx_relative or os.path.join(self.source_dir, "funkin", "backend", "system", "Main.hx")
        self.main_hx_path = os.path.join(self.output_path, self.main_hx_relative)
        self.patch_project = patch_project
        self.patch_main = patch_main
        self.results = []

    def validate_output(self):
        if not os.path.isdir(self.output_path):
            raise FileNotFoundError(f"CodenameEngine repository not found: {self.output_path}")

        if not os.path.isfile(self.project_xml_path):
            print("Warning: project.xml not found — is this really a CodenameEngine checkout?")

    def write_file(self, file_name, content):
        os.makedirs(self.target_dir, exist_ok=True)
        file_path = os.path.join(self.target_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"Created {file_path}")

    def run_hitbox_and_storage(self):
        try:
            self.write_file("Hitbox.hx", HITBOX_HX)
            self.write_file("StorageUtil.hx", STORAGE_UTIL_HX)
            self.results.append(("Hitbox.hx + StorageUtil.hx", True, ""))
        except Exception as error:
            self.results.append(("Hitbox.hx + StorageUtil.hx", False, str(error)))

    def run_project_patch(self):
        if not self.patch_project:
            return

        try:
            converter = ProjectCodename.ProjectCodenameConverter(self.project_xml_path)
            converter.patch()
            self.results.append(("project.xml patch", True, ""))
        except Exception as error:
            self.results.append(("project.xml patch", False, str(error)))

    def run_main_patch(self):
        if not self.patch_main:
            return

        try:
            converter = MainCodename.MainCodenameConverter(self.main_hx_path)
            converter.patch()
            self.results.append(("Main.hx patch", True, ""))
        except Exception as error:
            self.results.append(("Main.hx patch", False, str(error)))

    def run(self):
        self.validate_output()

        self.run_hitbox_and_storage()
        self.run_project_patch()
        self.run_main_patch()

        print("\n" + "=" * 40)
        print("Summary")
        print("=" * 40)
        for name, success, detail in self.results:
            status = "OK" if success else "FAILED"
            print(f"[{status}] {name}" + (f" — {detail}" if detail and not success else ""))

        print(f"\nCodenameEngine mobile conversion done at {self.output_path}")
        print("Reminder: Hitbox.hx still needs to be wired manually into PlayState.hx (or wherever note input is read).")


def parse_args():
    parser = argparse.ArgumentParser(description="Convert a CodenameEngine checkout for mobile")
    parser.add_argument("output", help="Path to the local CodenameEngine repository")
    parser.add_argument("--source-dir", default="source", help="Relative source folder inside the repository")
    parser.add_argument("--main-hx", help="Relative path to Main.hx (default: source/funkin/backend/system/Main.hx)")
    parser.add_argument("--no-project-patch", action="store_true", help="Skip patching project.xml")
    parser.add_argument("--no-main-patch", action="store_true", help="Skip patching Main.hx")
    return parser.parse_args()


def main():
    args = parse_args()
    generator = CodenameConverterGenerator(
        args.output,
        source_dir=args.source_dir,
        main_hx_relative=args.main_hx,
        patch_project=not args.no_project_patch,
        patch_main=not args.no_main_patch,
    )

    try:
        generator.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
