#!/bin/bash
# ------------------------------------------------------------------
#  Flrig EMCOMM - build from this source folder and install, in one command.
#     bash linux_install.sh            build the .tar.gz, install it into
#                                      ~/Applications/Flrig EMCOMM Ver <ver>, start it
#     bash linux_install.sh --remove   uninstall (your station list is kept)
#  Users without the source code install the release .tar.gz instead
#  (docs/Installing_Flrig_EMCOMM_on_Linux.pdf). Both end up in the same place.
#  First time only:  sudo apt install python3-tk python3-venv
# ------------------------------------------------------------------
set -e
cd "$(dirname "$0")"
chmod +x ./*.sh 2>/dev/null || true          # zips made on Windows lose these marks
sed -i 's/\r$//' ./*.sh packaging/*.sh 2>/dev/null || true

if [ "$1" = "--remove" ]; then
  sh packaging/linux_install.sh --remove
  exit 0
fi

if ! python3 -c "import tkinter" 2>/dev/null || ! python3 -c "import venv, ensurepip" 2>/dev/null; then
  echo "First run this, then run this script again:"
  echo "   sudo apt install python3-tk python3-venv"
  exit 1
fi

VER=$(grep -o 'APP_VERSION = "[^"]*"' flrig_emcomm/__init__.py | cut -d'"' -f2)
bash build_linux.sh
F="output/FlrigEMCOMM_Ver_${VER}_Linux.tar.gz"
mkdir -p ~/Applications
rm -rf ~/Applications/"Flrig EMCOMM Ver $VER"
tar -xzf "$F" -C ~/Applications
sh ~/Applications/"Flrig EMCOMM Ver $VER"/linux_install.sh
