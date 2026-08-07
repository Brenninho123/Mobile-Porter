[app]
title = Mobile-Porter
package.name = mobileporter
package.domain = com.brenninho

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = .github,.git,ports,dist,build,__pycache__,.buildozer

version = 1.0.0

requirements = python3

orientation = portrait
fullscreen = 0

android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
