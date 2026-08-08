import argparse
import os
import sys


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
    def __init__(self, output_path, source_dir="source"):
        self.output_path = os.path.abspath(output_path)
        self.source_dir = source_dir
        self.target_dir = os.path.join(self.output_path, self.source_dir, "mobileporter")

    def validate_output(self):
        if not os.path.isdir(self.output_path):
            raise FileNotFoundError(f"CodenameEngine repository not found: {self.output_path}")

        project_xml = os.path.join(self.output_path, "project.xml")
        if not os.path.isfile(project_xml):
            print("Warning: project.xml not found — is this really a CodenameEngine checkout?")

    def write_file(self, file_name, content):
        file_path = os.path.join(self.target_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"Created {file_path}")

    def run(self):
        self.validate_output()
        os.makedirs(self.target_dir, exist_ok=True)

        self.write_file("Hitbox.hx", HITBOX_HX)
        self.write_file("StorageUtil.hx", STORAGE_UTIL_HX)

        print(f"CodenameEngine mobile files generated at {self.target_dir}")
        print("Hitbox.hx exposes pressed()/justPressed()/justReleased() per direction — wire these into wherever CodenameEngine reads note input (likely PlayState or its Controls class).")
        print("StorageUtil.hx wraps openfl.net.SharedObject — swap in wherever CodenameEngine currently reads/writes save data or settings directly to disk.")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate mobile compat files for a CodenameEngine checkout")
    parser.add_argument("output", help="Path to the local CodenameEngine repository")
    parser.add_argument("--source-dir", default="source", help="Relative source folder inside the repository")
    return parser.parse_args()


def main():
    args = parse_args()
    generator = CodenameConverterGenerator(args.output, args.source_dir)

    try:
        generator.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
