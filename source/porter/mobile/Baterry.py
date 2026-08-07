import argparse
import ctypes
import os
import sys
import time


class SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("Reserved1", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def get_battery_status_windows():
    status = SystemPowerStatus()
    result = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.pointer(status))

    if not result:
        return None

    if status.BatteryLifePercent == 255:
        return None

    return {
        "level": status.BatteryLifePercent,
        "charging": status.ACLineStatus == 1,
        "source": "windows",
    }


def get_battery_status_linux_like():
    power_supply_dir = "/sys/class/power_supply"

    if not os.path.isdir(power_supply_dir):
        return None

    for entry in os.listdir(power_supply_dir):
        capacity_path = os.path.join(power_supply_dir, entry, "capacity")
        status_path = os.path.join(power_supply_dir, entry, "status")

        if not os.path.isfile(capacity_path):
            continue

        try:
            with open(capacity_path, "r", encoding="utf-8") as file:
                level = int(file.read().strip())
        except (ValueError, OSError):
            continue

        charging = False
        if os.path.isfile(status_path):
            try:
                with open(status_path, "r", encoding="utf-8") as file:
                    charging = file.read().strip().lower() in ("charging", "full")
            except OSError:
                pass

        return {
            "level": level,
            "charging": charging,
            "source": entry,
        }

    return None


def get_battery_status():
    if sys.platform == "win32":
        return get_battery_status_windows()

    if sys.platform.startswith("linux") or "ANDROID_ARGUMENT" in os.environ:
        return get_battery_status_linux_like()

    return None


class PowerSaver:
    def __init__(self, low_threshold=20, critical_threshold=10, poll_interval=30):
        self.low_threshold = low_threshold
        self.critical_threshold = critical_threshold
        self.poll_interval = poll_interval
        self.last_status = None
        self.last_check_time = 0

    def refresh(self, force=False):
        now = time.time()

        if not force and (now - self.last_check_time) < self.poll_interval:
            return self.last_status

        self.last_status = get_battery_status()
        self.last_check_time = now
        return self.last_status

    def is_low_power(self):
        status = self.refresh()

        if status is None or status["charging"]:
            return False

        return status["level"] <= self.low_threshold

    def is_critical_power(self):
        status = self.refresh()

        if status is None or status["charging"]:
            return False

        return status["level"] <= self.critical_threshold

    def throttle_delay(self):
        if self.is_critical_power():
            return 0.15
        if self.is_low_power():
            return 0.05
        return 0.0

    def wait_if_needed(self):
        delay = self.throttle_delay()
        if delay > 0:
            time.sleep(delay)


def print_status():
    status = get_battery_status()

    if status is None:
        print("Battery status: unavailable on this platform")
        return

    charging_label = "charging" if status["charging"] else "not charging"
    print(f"Battery: {status['level']}% ({charging_label}, source: {status['source']})")


def parse_args():
    parser = argparse.ArgumentParser(description="Read system battery status and power-saving helpers")
    parser.add_argument("--watch", action="store_true", help="Continuously print battery status")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between checks in --watch mode")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.watch:
        try:
            while True:
                print_status()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            pass
    else:
        print_status()


if __name__ == "__main__":
    main()
