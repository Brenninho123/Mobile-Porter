APP_TITLE = "Mobile-Porter"
APP_FILE = "Main"

PACKAGE_DOMAIN = "com.brenninho"
PACKAGE_NAME = "mobileporter"
PACKAGE = f"{PACKAGE_DOMAIN}.{PACKAGE_NAME}"

VERSION = "1.0.0"
COMPANY = "Brenninho"

ICON_PATH = "assets/icon/icon.png"

ORIENTATION = "portrait"
FULLSCREEN = False

PERMISSIONS = [
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_EXTERNAL_STORAGE",
]

ASSETS_DIR = "assets"
SOURCE_DIR = "source"

SUPPORTED_PLATFORMS = ["android", "ios"]

ANDROID_API = 34
ANDROID_MINAPI = 21
ANDROID_NDK = "25b"
ANDROID_ARCHS = ["arm64-v8a", "armeabi-v7a"]
