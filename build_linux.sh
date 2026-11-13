#!/usr/bin/env bash
# ------------------------------------------------------------------
#  Flrig EMCOMM - Linux build. From the project folder:
#     bash build_linux.sh              makes output/FlrigEMCOMM_Ver_<ver>_Linux.tar.gz
#     bash build_linux.sh --appimage   also makes output/FlrigEMCOMM-x86_64.AppImage
#  The .tar.gz holds the ready-built program in a folder "Flrig EMCOMM Ver <ver>"
#  plus linux_install.sh. Users unpack it into ~/Applications and run that script
#  (see docs/Installing_Flrig_EMCOMM_on_Linux.pdf). To build AND install on this PC: bash linux_install.sh
#  Build on the OLDEST Linux you want to support (GitHub uses Ubuntu 22.04).
#  First time:  sudo apt install python3-tk python3-venv
# ------------------------------------------------------------------
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
NAME=FlrigEMCOMM
APPIMAGE=""; [ "$1" = "--appimage" ] && APPIMAGE=1
"$PY" -c "import tkinter" 2>/dev/null || { echo "First run:  sudo apt install python3-tk python3-venv"; exit 1; }
VER=$(grep -o 'APP_VERSION = "[^"]*"' flrig_emcomm/__init__.py | cut -d'"' -f2)
TOP="Flrig EMCOMM Ver $VER"
TGZ="output/${NAME}_Ver_${VER}_Linux.tar.gz"
sed -i 's/\r$//' ./*.sh packaging/*.sh 2>/dev/null || true   # Windows line endings break scripts
echo "Building Flrig EMCOMM $VER"

echo "[1/3] Getting the build tools..."
[ -x .buildenv/bin/python ] || "$PY" -m venv .buildenv
.buildenv/bin/pip install --quiet --disable-pip-version-check --upgrade pip pyinstaller

echo "[2/3] Building the program (about a minute)..."
rm -rf build "dist/$NAME" AppDir
.buildenv/bin/python -m PyInstaller --noconfirm --clean --onedir --windowed --name "$NAME" \
    --specpath build --add-data "$PWD/flrig_emcomm/assets:flrig_emcomm/assets" \
    --add-data "$PWD/flrig_emcomm/data:flrig_emcomm/data" \
    --collect-submodules flrig_emcomm run.py > build_log.txt 2>&1 \
    || { echo "Build failed. See build_log.txt"; exit 1; }

echo "[3/3] Packing $TGZ..."
mkdir -p output
rm -rf "output/$TOP" "$TGZ"
mkdir -p "output/$TOP"
cp -a "dist/$NAME/." "output/$TOP/"
cp flrig_emcomm/assets/icon_256.png "output/$TOP/icon.png"
sed "s/@VERSION@/$VER/" packaging/linux_install.sh > "output/$TOP/linux_install.sh"
for g in Installing_Flrig_EMCOMM_on_Linux.pdf Flrig_EMCOMM_User_Guide.pdf; do
  [ -f "docs/$g" ] && cp "docs/$g" "output/$TOP/"
done
chmod +x "output/$TOP/$NAME" "output/$TOP/linux_install.sh"
tar -C output -czf "$TGZ" "$TOP"
rm -rf "output/$TOP"

if [ -n "$APPIMAGE" ]; then
  echo "[+] Packing the AppImage..."
  if [ ! -x .appimagetool ]; then
    URL=https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    (curl -fsSL -o .appimagetool "$URL" || wget -q -O .appimagetool "$URL") \
      || { echo "Could not download appimagetool (needs internet)."; exit 1; }
    chmod +x .appimagetool
  fi
  mkdir -p AppDir/usr/bin
  cp -a "dist/$NAME/." AppDir/usr/bin/
  cp flrig_emcomm/assets/icon_256.png AppDir/flrig-emcomm.png
  cp AppDir/flrig-emcomm.png AppDir/.DirIcon
  cp packaging/flrig-emcomm.desktop AppDir/
  printf '#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec "$HERE/usr/bin/%s" "$@"\n' "$NAME" > AppDir/AppRun
  chmod +x AppDir/AppRun
  rm -f "output/$NAME-x86_64.AppImage"
  APPIMAGE_EXTRACT_AND_RUN=1 ARCH=x86_64 ./.appimagetool --no-appstream AppDir \
      "output/$NAME-x86_64.AppImage" >> build_log.txt 2>&1 \
      || { echo "Packing the AppImage failed. See build_log.txt"; exit 1; }
  chmod +x "output/$NAME-x86_64.AppImage"
fi

rm -rf build "dist/$NAME" AppDir build_log.txt
echo
echo "Done!  $TGZ"
[ -n "$APPIMAGE" ] && echo "       output/$NAME-x86_64.AppImage"
exit 0
