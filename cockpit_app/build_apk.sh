#!/usr/bin/env bash
#
# Build the Cockpit APK WITHOUT Gradle — aapt2 → javac → d8 → zipalign →
# apksigner. The app is plain Java with zero library dependencies, so this
# direct toolchain build is fast and avoids Gradle's daemon entirely.
#
# Output: manual_build/cockpit-debug.apk
#
# Auto-detects the Android SDK and Android Studio's bundled JDK. Override with
# ANDROID_SDK_ROOT / JAVA_HOME if needed.
#
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
cd "$HERE"

SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Library/Android/sdk}}"
[ -d "$SDK" ] || { echo "ERROR: Android SDK not found at $SDK"; exit 1; }
if [ -z "${JAVA_HOME:-}" ]; then
  JBR="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
  [ -x "$JBR/bin/javac" ] && export JAVA_HOME="$JBR"
fi
[ -x "$JAVA_HOME/bin/javac" ] || { echo "ERROR: no JDK (set JAVA_HOME)"; exit 1; }

# Pick the highest build-tools for d8 (newer d8 fixes a JDK-21 bytecode NPE),
# and a platform android.jar.
pick_max() { ls "$1" 2>/dev/null | sort -V | tail -1; }
BT_AAPT="$SDK/build-tools/$(pick_max "$SDK/build-tools")"   # newest for everything
ANDROID_JAR="$SDK/platforms/$(pick_max "$SDK/platforms")/android.jar"
echo "SDK=$SDK"; echo "build-tools=$BT_AAPT"; echo "android.jar=$ANDROID_JAR"; echo "JDK=$JAVA_HOME"

APP="app/src/main"; OUT="manual_build"
PKG="com.josephine.cockpit"
rm -rf "$OUT"; mkdir -p "$OUT/gen" "$OUT/obj"

echo "==> [1/7] generate dashboard from latest portal_data/"
( cd "$REPO" && python3 -m cockpit.build_cockpit >/dev/null )

echo "==> [2/7] manifest (inject package for aapt2)"
sed "s/<manifest /<manifest package=\"$PKG\" /" "$APP/AndroidManifest.xml" > "$OUT/AndroidManifest.xml"

echo "==> [3/7] aapt2 compile + link (res + assets)"
"$BT_AAPT/aapt2" compile --dir "$APP/res" -o "$OUT/res.zip"
"$BT_AAPT/aapt2" link -o "$OUT/base.apk" -I "$ANDROID_JAR" \
  --manifest "$OUT/AndroidManifest.xml" -A "$APP/assets" --java "$OUT/gen" \
  --min-sdk-version 24 --target-sdk-version 34 --version-code 1 --version-name 1.0 \
  "$OUT/res.zip"

echo "==> [4/7] javac"
"$JAVA_HOME/bin/javac" -source 11 -target 11 -classpath "$ANDROID_JAR" -d "$OUT/obj" \
  "$APP/java/com/josephine/cockpit/MainActivity.java" $(find "$OUT/gen" -name "R.java")

echo "==> [5/7] d8 → classes.dex"
"$BT_AAPT/d8" --min-api 24 --output "$OUT/" $(find "$OUT/obj" -name "*.class")

echo "==> [6/7] package dex + zipalign"
cp "$OUT/base.apk" "$OUT/app-unsigned.apk"
( cd "$OUT" && zip -qj app-unsigned.apk classes.dex )
"$BT_AAPT/zipalign" -f 4 "$OUT/app-unsigned.apk" "$OUT/app-aligned.apk"

echo "==> [7/7] sign (debug key)"
KS="$HOME/.android/debug.keystore"
[ -f "$KS" ] || "$JAVA_HOME/bin/keytool" -genkeypair -keystore "$KS" -storepass android \
  -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Android Debug,O=Android,C=US"
"$BT_AAPT/apksigner" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias androiddebugkey --out "$OUT/cockpit-debug.apk" "$OUT/app-aligned.apk"
"$BT_AAPT/apksigner" verify "$OUT/cockpit-debug.apk" >/dev/null && echo "✅ $OUT/cockpit-debug.apk (signed + verified)"
