import argparse
import os
import subprocess
import sys


class ASTCConverter:
    def __init__(self, input_dir, output_dir, block_size, quality, astcenc_path):
        self.input_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.block_size = block_size
        self.quality = quality
        self.astcenc_path = astcenc_path

    def validate_input(self):
        if not os.path.isdir(self.input_dir):
            raise FileNotFoundError(f"Input directory not found: {self.input_dir}")

    def find_png_files(self):
        png_files = []
        for root, _, files in os.walk(self.input_dir):
            for file_name in files:
                if file_name.lower().endswith(".png"):
                    png_files.append(os.path.join(root, file_name))
        return png_files

    def output_path_for(self, png_path):
        relative_path = os.path.relpath(png_path, self.input_dir)
        relative_astc = os.path.splitext(relative_path)[0] + ".astc"
        return os.path.join(self.output_dir, relative_astc)

    def needs_conversion(self, png_path, astc_path):
        if not os.path.isfile(astc_path):
            return True
        return os.path.getmtime(png_path) > os.path.getmtime(astc_path)

    def convert_file(self, png_path, astc_path):
        os.makedirs(os.path.dirname(astc_path), exist_ok=True)

        command = [
            self.astcenc_path,
            "-cl",
            png_path,
            astc_path,
            self.block_size,
            self.quality,
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"astcenc failed for {png_path}: {result.stderr.strip()}")

    def run(self):
        self.validate_input()
        png_files = self.find_png_files()

        converted_count = 0
        skipped_count = 0

        for png_path in png_files:
            astc_path = self.output_path_for(png_path)

            if self.needs_conversion(png_path, astc_path):
                self.convert_file(png_path, astc_path)
                converted_count += 1
                print(f"Converted: {os.path.relpath(png_path, self.input_dir)}")
            else:
                skipped_count += 1

        print(f"Done. Converted: {converted_count}, Skipped: {skipped_count}")


def parse_args():
    parser = argparse.ArgumentParser(description="Convert PNG assets to ASTC")
    parser.add_argument("input", help="Directory containing PNG files")
    parser.add_argument("output", help="Directory to write ASTC files (mirrors input structure)")
    parser.add_argument("--block-size", default="6x6", help="ASTC block size, e.g. 4x4, 6x6, 8x8")
    parser.add_argument("--quality", default="-medium", help="astcenc quality preset, e.g. -fast, -medium, -thorough")
    parser.add_argument("--astcenc-path", default="astcenc", help="Path to the astcenc executable")
    return parser.parse_args()


def main():
    args = parse_args()
    converter = ASTCConverter(args.input, args.output, args.block_size, args.quality, args.astcenc_path)

    try:
        converter.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
