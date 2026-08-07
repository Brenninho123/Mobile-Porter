import argparse
import os
import sys


TOUCH_BUTTON_HX = """package mobileporter;

import flixel.FlxSprite;
import flixel.FlxG;
import flixel.math.FlxPoint;

class TouchButton extends FlxSprite
{
	public var buttonID:String;
	public var pressed:Bool = false;
	public var justPressed:Bool = false;
	public var justReleased:Bool = false;

	var wasPressed:Bool = false;

	public function new(x:Float, y:Float, buttonID:String, ?graphicPath:String)
	{
		super(x, y);
		this.buttonID = buttonID;

		if (graphicPath != null)
			loadGraphic(graphicPath);
		else
			makeGraphic(80, 80, 0x88FFFFFF);

		scrollFactor.set();
		alpha = 0.6;
	}

	override public function update(elapsed:Float):Void
	{
		super.update(elapsed);

		pressed = false;

		for (touch in FlxG.touches.list)
		{
			if (overlapsPoint(FlxPoint.get(touch.x, touch.y)))
			{
				pressed = true;
				break;
			}
		}

		justPressed = pressed && !wasPressed;
		justReleased = !pressed && wasPressed;
		wasPressed = pressed;

		alpha = pressed ? 1 : 0.6;
	}
}
"""

MOBILE_CONTROLS_HX = """package mobileporter;

import flixel.FlxG;
import flixel.group.FlxGroup;

class MobileControls extends FlxGroup
{
	public var left:TouchButton;
	public var right:TouchButton;
	public var up:TouchButton;
	public var down:TouchButton;

	public function new()
	{
		super();

		var screenW = FlxG.width;
		var screenH = FlxG.height;

		left = new TouchButton(20, screenH - 100, "left");
		down = new TouchButton(110, screenH - 100, "down");
		up = new TouchButton(screenW - 200, screenH - 100, "up");
		right = new TouchButton(screenW - 100, screenH - 100, "right");

		add(left);
		add(down);
		add(up);
		add(right);
	}

	public function isPressed(buttonID:String):Bool
	{
		return switch (buttonID)
		{
			case "left": left.pressed;
			case "down": down.pressed;
			case "up": up.pressed;
			case "right": right.pressed;
			default: false;
		}
	}

	public function isJustPressed(buttonID:String):Bool
	{
		return switch (buttonID)
		{
			case "left": left.justPressed;
			case "down": down.justPressed;
			case "up": up.justPressed;
			case "right": right.justPressed;
			default: false;
		}
	}
}
"""


class ControlsGenerator:
    def __init__(self, output_path, source_dir):
        self.output_path = os.path.abspath(output_path)
        self.source_dir = source_dir
        self.target_dir = os.path.join(self.output_path, self.source_dir, "mobileporter")

    def validate_output(self):
        if not os.path.isdir(self.output_path):
            raise FileNotFoundError(f"Output project not found: {self.output_path}")

    def write_file(self, file_name, content):
        file_path = os.path.join(self.target_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"Created {file_path}")

    def run(self):
        self.validate_output()
        os.makedirs(self.target_dir, exist_ok=True)

        self.write_file("TouchButton.hx", TOUCH_BUTTON_HX)
        self.write_file("MobileControls.hx", MOBILE_CONTROLS_HX)

        print(f"Mobile controls generated at {self.target_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate mobile touch controls into the ported project")
    parser.add_argument("output", help="Path to the ported project")
    parser.add_argument("--source-dir", default="source", help="Relative source folder inside the ported project")
    return parser.parse_args()


def main():
    args = parse_args()
    generator = ControlsGenerator(args.output, args.source_dir)

    try:
        generator.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
