import argparse
import importlib.util
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MOBILE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "mobile"))


def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Battery = load_module("Battery", os.path.join(MOBILE_DIR, "Battery.py"))


class ASTCConverter:
    def __init__(self, input_dir, output_dir, block_size, quality, astcenc_path,
                 max_workers=4, retry_once=True, power_saver=None):
        self.input_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.block_size = block_size
        self.quality = quality
        self.astcenc_path = astcenc_path
        self.max_workers = max_workers
        self.retry_once = retry_once
        self.power_saver = power_saver if power_saver else Battery.PowerSaver()

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
            raise RuntimeError(result.stderr.strip())

    def convert_with_retry(self, png_path):
        astc_path = self.output_path_for(png_path)

        if not self.needs_conversion(png_path, astc_path):
            return (png_path, "skipped", None)

        try:
            self.convert_file(png_path, astc_path)
            return (png_path, "converted", None)
        except RuntimeError as error:
            if not self.retry_once:
                return (png_path, "failed", str(error))

            try:
                self.convert_file(png_path, astc_path)
                return (png_path, "converted", None)
            except RuntimeError as retry_error:
                return (png_path, "failed", str(retry_error))

    def effective_worker_count(self):
        if self.power_saver.is_critical_power():
            return 1
        if self.power_saver.is_low_power():
            return min(2, self.max_workers)
        return self.max_workers

    def run(self):
        self.validate_input()
        png_files = self.find_png_files()

        total = len(png_files)
        converted_count = 0
        skipped_count = 0
        failed_count = 0

        worker_count = self.effective_worker_count()

        if worker_count <= 1:
            for index, png_path in enumerate(png_files, start=1):
                relative = os.path.relpath(png_path, self.input_dir)
                png_path, status, error = self.convert_with_retry(png_path)

                if status == "converted":
                    converted_count += 1
                    print(f"[{index}/{total}] Converted: {relative}")
                elif status == "skipped":
                    skipped_count += 1
                else:
                    failed_count += 1
                    print(f"[{index}/{total}] Failed: {relative} — {error}")

                self.power_saver.wait_if_needed()
        else:
            completed = 0
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = {executor.submit(self.convert_with_retry, png_path): png_path for png_path in png_files}

                for future in as_completed(futures):
                    completed += 1
                    png_path, status, error = future.result()
                    relative = os.path.relpath(png_path, self.input_dir)

                    if status == "converted":
                        converted_count += 1
                        print(f"[{completed}/{total}] Converted: {relative}")
                    elif status == "skipped":
                        skipped_count += 1
                    else:
                        failed_count += 1
                        print(f"[{completed}/{total}] Failed: {relative} — {error}")

        print(f"Done. Converted: {converted_count}, Skipped: {skipped_count}, Failed: {failed_count} (workers: {worker_count})")

        if failed_count > 0:
            raise RuntimeError(f"{failed_count} file(s) failed to convert")


def parse_args():
    parser = argparse.ArgumentParser(description="Convert PNG assets to ASTC")
    parser.add_argument("input", help="Directory containing PNG files")
    parser.add_argument("output", help="Directory to write ASTC files (mirrors input structure)")
    parser.add_argument("--block-size", default="6x6", help="ASTC block size, e.g. 4x4, 6x6, 8x8")
    parser.add_argument("--quality", default="-medium", help="astcenc quality preset, e.g. -fast, -medium, -thorough")
    parser.add_argument("--astcenc-path", default="astcenc", help="Path to the astcenc executable")
    parser.add_argument("--max-workers", type=int, default=4, help="Max parallel conversions when battery allows")
    parser.add_argument("--no-retry", action="store_true", help="Do not retry failed conversions")
    return parser.parse_args()


def main():
    args = parse_args()
    converter = ASTCConverter(
        args.input, args.output, args.block_size, args.quality, args.astcenc_path,
        max_workers=args.max_workers, retry_once=not args.no_retry,
    )

    try:
        converter.run()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
