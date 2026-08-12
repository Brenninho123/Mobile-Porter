import argparse
import json
import os
import sys


DEFAULT_LAYOUT = {
    "buttons": [
        {"id": "left", "key": "left", "shape": "square", "xPercent": 0.06, "yPercent": 0.82, "size": 70},
        {"id": "down", "key": "down", "shape": "square", "xPercent": 0.17, "yPercent": 0.82, "size": 70},
        {"id": "up", "key": "up", "shape": "square", "xPercent": 0.75, "yPercent": 0.82, "size": 70},
        {"id": "right", "key": "right", "shape": "square", "xPercent": 0.86, "yPercent": 0.82, "size": 70},
        {"id": "accept", "key": "accept", "shape": "circle", "xPercent": 0.92, "yPercent": 0.60, "size": 60},
        {"id": "back", "key": "back", "shape": "circle", "xPercent": 0.04, "yPercent": 0.08, "size": 50},
    ],
    "opacityIdle": 0.5,
    "opacityPressed": 1.0,
    "vibrateOnPress": True,
    "vibrateDurationMs": 20,
}


TOUCH_BUTTON_HX = """package mobileporter;

import flixel.FlxSprite;
import flixel.FlxG;
import flixel.tweens.FlxTween;
import lime.system.System;

class TouchButton extends FlxSprite
{
	public var buttonID:String;
	public var pressed:Bool = false;
	public var justPressed:Bool = false;
	public var justReleased:Bool = false;
	public var editable:Bool = false;

	var wasPressed:Bool = false;
	var activeTouchID:Int = -1;
	var opacityIdle:Float;
	var opacityPressed:Float;
	var vibrateOnPress:Bool;
	var vibrateDurationMs:Int;
	var dragOffsetX:Float = 0;
	var dragOffsetY:Float = 0;

	public function new(x:Float, y:Float, size:Int, buttonID:String, opacityIdle:Float, opacityPressed:Float,
		vibrateOnPress:Bool, vibrateDurationMs:Int, ?graphicPath:String)
	{
		super(x, y);
		this.buttonID = buttonID;
		this.opacityIdle = opacityIdle;
		this.opacityPressed = opacityPressed;
		this.vibrateOnPress = vibrateOnPress;
		this.vibrateDurationMs = vibrateDurationMs;

		if (graphicPath != null)
			loadGraphic(graphicPath);
		else
			makeGraphic(size, size, 0x88FFFFFF);

		scrollFactor.set();
		alpha = opacityIdle;
	}

	override public function update(elapsed:Float):Void
	{
		super.update(elapsed);

		if (editable)
		{
			updateDrag();
			return;
		}

		updateTouchState();
	}

	function containsTouch(touch:flixel.input.touch.FlxTouch):Bool
	{
		return touch.x >= x && touch.x <= x + width && touch.y >= y && touch.y <= y + height;
	}

	function updateTouchState():Void
	{
		pressed = false;

		for (touch in FlxG.touches.list)
		{
			if (containsTouch(touch))
			{
				pressed = true;
				activeTouchID = touch.touchPointID;
				break;
			}
		}

		justPressed = pressed && !wasPressed;
		justReleased = !pressed && wasPressed;

		if (justPressed && vibrateOnPress)
			vibrate();

		wasPressed = pressed;

		alpha = pressed ? opacityPressed : opacityIdle;
	}

	function updateDrag():Void
	{
		for (touch in FlxG.touches.list)
		{
			if (touch.justPressed && containsTouch(touch))
			{
				activeTouchID = touch.touchPointID;
				dragOffsetX = x - touch.x;
				dragOffsetY = y - touch.y;
			}

			if (touch.touchPointID == activeTouchID && touch.pressed)
			{
				x = touch.x + dragOffsetX;
				y = touch.y + dragOffsetY;
			}

			if (touch.touchPointID == activeTouchID && touch.justReleased)
				activeTouchID = -1;
		}
	}

	function vibrate():Void
	{
		#if android
		System.vibrate(vibrateDurationMs / 1000);
		#end
	}

	public function fadeTo(targetAlpha:Float, duration:Float = 0.3):Void
	{
		FlxTween.tween(this, {alpha: targetAlpha}, duration);
	}
}
"""

MOBILE_CONTROLS_HX = """package mobileporter;

import flixel.FlxG;
import flixel.group.FlxGroup;
import flixel.util.FlxSave;
import haxe.Json;
import openfl.Assets;

typedef ButtonLayout =
{
	id:String,
	key:String,
	shape:String,
	xPercent:Float,
	yPercent:Float,
	size:Int
}

typedef ControlsLayout =
{
	buttons:Array<ButtonLayout>,
	opacityIdle:Float,
	opacityPressed:Float,
	vibrateOnPress:Bool,
	vibrateDurationMs:Int
}

class MobileControls extends FlxGroup
{
	public var buttons:Map<String, TouchButton> = new Map();
	public var editMode:Bool = false;

	var save:FlxSave;

	public function new(layoutPath:String = "assets/data/controls_layout.json")
	{
		super();

		save = new FlxSave();
		save.bind("mobileporter_controls");

		var layout = loadLayout(layoutPath);
		buildButtons(layout);
	}

	function loadLayout(layoutPath:String):ControlsLayout
	{
		var raw = Assets.getText(layoutPath);
		return Json.parse(raw);
	}

	function buildButtons(layout:ControlsLayout):Void
	{
		var screenW = FlxG.width;
		var screenH = FlxG.height;

		for (buttonData in layout.buttons)
		{
			var posX = screenW * buttonData.xPercent;
			var posY = screenH * buttonData.yPercent;

			if (save.data.positions != null && Reflect.hasField(save.data.positions, buttonData.id))
			{
				var savedPos = Reflect.field(save.data.positions, buttonData.id);
				posX = savedPos.x;
				posY = savedPos.y;
			}

			var button = new TouchButton(
				posX, posY, buttonData.size, buttonData.id,
				layout.opacityIdle, layout.opacityPressed,
				layout.vibrateOnPress, layout.vibrateDurationMs
			);

			buttons.set(buttonData.id, button);
			add(button);
		}
	}

	public function isPressed(buttonID:String):Bool
	{
		var button = buttons.get(buttonID);
		return button != null && button.pressed;
	}

	public function isJustPressed(buttonID:String):Bool
	{
		var button = buttons.get(buttonID);
		return button != null && button.justPressed;
	}

	public function isJustReleased(buttonID:String):Bool
	{
		var button = buttons.get(buttonID);
		return button != null && button.justReleased;
	}

	public function setEditMode(enabled:Bool):Void
	{
		editMode = enabled;
		for (button in buttons)
			button.editable = enabled;
	}

	public function saveLayout():Void
	{
		var positions:Dynamic = {};
		for (id in buttons.keys())
		{
			var button = buttons.get(id);
			Reflect.setField(positions, id, {x: button.x, y: button.y});
		}
		save.data.positions = positions;
		save.flush();
	}

	public function resetLayout():Void
	{
		save.data.positions = null;
		save.flush();
	}

	public function show():Void
	{
		for (button in buttons)
			button.visible = true;
	}

	public function hide():Void
	{
		for (button in buttons)
			button.visible = false;
	}
}
"""


class ControlsGenerator:
    def __init__(self, output_path, source_dir, assets_dir="assets", layout=None):
        self.output_path = os.path.abspath(output_path)
        self.source_dir = source_dir
        self.assets_dir = assets_dir
        self.layout = layout if layout else DEFAULT_LAYOUT
        self.target_dir = os.path.join(self.output_path, self.source_dir, "mobileporter")
        self.data_dir = os.path.join(self.output_path, self.assets_dir, "data")

    def validate_output(self):
        if not os.path.isdir(self.output_path):
            raise FileNotFoundError(f"Output project not found: {self.output_path}")

    def write_file(self, file_path, content):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"Created {file_path}")

    def write_layout_json(self):
        layout_path = os.path.join(self.data_dir, "controls_layout.json")
        self.write_file(layout_path, json.dumps(self.layout, indent=4))

    def run(self):
        self.validate_output()
        os.makedirs(self.target_dir, exist_ok=True)

        self.write_file(os.path.join(self.target_dir, "TouchButton.hx"), TOUCH_BUTTON_HX)
        self.write_file(os.path.join(self.target_dir, "MobileControls.hx"), MOBILE_CONTROLS_HX)
        self.write_layout_json()

        print(f"Mobile controls generated at {self.target_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate mobile touch controls into the ported project")
    parser.add_argument("output", help="Path to the ported project")
    parser.add_argument("--source-dir", default="source", help="Relative source folder inside the ported project")
    parser.add_argument("--assets-dir", default="assets", help="Relative assets folder inside the ported project")
    parser.add_argument("--layout", help="Path to a custom JSON layout file (overrides the default layout)")
    return parser.parse_args()


def load_custom_layout(layout_path):
    with open(layout_path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    args = parse_args()
    layout = load_custom_layout(args.layout) if args.layout else None
    generator = ControlsGenerator(args.output, args.source_dir, args.assets_dir, layout)

    try:
        generator.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
