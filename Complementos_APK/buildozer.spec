[app]
title = PiktaSoftMobile
package.name = piktasoft
package.domain = org.pikta
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,mp4,avi,mov
version = 1.1.9

# Icono de la aplicación
icon.filename = logo.png

# REQUERIMIENTOS: Se añadió pyjnius, requests y requests-toolbelt
requirements = python3,kivy,pillow,pyjnius,openssl,urllib3,requests,requests-toolbelt

# Orientación: Volvemos a portrait para asegurar la compilación
orientation = landscape
fullscreen = 0

# PERMISOS: Se mantienen los de Bluetooth e Internet
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN

# PERMITIR HTTP (Para que cargue la publicidad desde tu IP local)
android.manifest.attributes = android:usesCleartextTraffic="true"

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
