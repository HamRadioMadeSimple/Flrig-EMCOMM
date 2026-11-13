#!/bin/sh
# ------------------------------------------------------------------
#  Flrig EMCOMM @VERSION@ - Linux installer (inside the release .tar.gz).
#  Unpack the .tar.gz into ~/Applications, then:
#     sh ~/Applications/"Flrig EMCOMM Ver @VERSION@"/linux_install.sh
#  Adds the app-menu entry and desktop icon for this folder and starts the app.
#  Offers to remove older versions. Never touches your station list, settings
#  or log, which live in ~/.local/share/flrig-emcomm.
#     sh .../linux_install.sh --remove   removes every version and the icons
#                                         (your station list is kept)
# ------------------------------------------------------------------
VER="@VERSION@"
NAME=FlrigEMCOMM
HERE=$(cd "$(dirname "$0")" && pwd)
APPS="$HOME/Applications"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/flrig-emcomm"
MENU="$HOME/.local/share/applications/flrig-emcomm.desktop"
DESKDIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
DESK="$DESKDIR/flrig-emcomm.desktop"

ask() {  # ask "question" -> 0 for y
  printf '%s [y/N] ' "$1"
  read -r ans < /dev/tty || ans=""
  case "$ans" in y|Y|yes|YES|Yes) return 0 ;; *) return 1 ;; esac
}

pkill -x "$NAME" 2>/dev/null && sleep 1

if [ "$1" = "--remove" ]; then
  rm -f "$MENU" "$DESK"
  # the old from-source install (version 1.18) kept the program here
  rm -rf "$DATA/$NAME" "$DATA/_internal" "$DATA/icon.png"
  for d in "$APPS"/"Flrig EMCOMM Ver "*; do
    [ -d "$d" ] && rm -rf "$d" && echo "Removed $d"
  done
  echo "Flrig EMCOMM removed. Your station list is kept in $DATA"
  exit 0
fi

if [ ! -x "$HERE/$NAME" ]; then
  chmod +x "$HERE/$NAME" 2>/dev/null
  [ -x "$HERE/$NAME" ] || { echo "STOP: $HERE/$NAME is missing. Unpack the whole .tar.gz again."; exit 1; }
fi

# Keep the station list safe: copy it from where older versions kept it, once
mkdir -p "$DATA"
if [ ! -f "$DATA/flrig_stations.json" ] && [ -f "$APPS/Flrig EMCOMM/flrig_stations.json" ]; then
  cp -p "$APPS/Flrig EMCOMM/flrig_stations.json" "$DATA/"
  echo "Copied your station list from $APPS/Flrig EMCOMM"
fi

# Older versions (never a newer one)
OLD=""
for d in "$APPS"/"Flrig EMCOMM Ver "*; do
  [ -d "$d" ] || continue
  [ "$d" = "$HERE" ] && continue
  v=${d##*Ver }
  newest=$(printf '%s\n%s\n' "$v" "$VER" | sort -V | tail -n 1)
  [ "$newest" = "$VER" ] && [ "$v" != "$VER" ] && OLD="$OLD$d
"
done
[ -x "$DATA/$NAME" ] && OLD="$OLD$DATA (program files of version 1.18)
"
[ -f "$APPS/Flrig EMCOMM/FlrigEMCOMM-x86_64.AppImage" ] && \
  OLD="$OLD$APPS/Flrig EMCOMM/FlrigEMCOMM-x86_64.AppImage
"

# Menu entry and desktop icon for this version
mkdir -p "$(dirname "$MENU")"
cat > "$MENU" <<EOF
[Desktop Entry]
Type=Application
Name=Flrig EMCOMM
Comment=Station list that tunes your radio through flrig
Exec="$HERE/$NAME"
Path=$HERE
Icon=$HERE/icon.png
Terminal=false
Categories=HamRadio;Network;Utility;
StartupWMClass=Flrigemcomm
EOF
chmod +x "$MENU"
if [ -d "$DESKDIR" ]; then
  cp "$MENU" "$DESK" && chmod +x "$DESK"
  gio set "$DESK" metadata::trusted true 2>/dev/null
fi
update-desktop-database "$(dirname "$MENU")" 2>/dev/null

echo
echo "Flrig EMCOMM $VER installed in $HERE"
echo "Menu entry and desktop icon added. Your station list lives in $DATA"

if [ -n "$OLD" ]; then
  echo
  echo "Older version found:"
  printf '%s' "$OLD" | sed 's/^/   /'
  if ask "Remove it? Your station list is kept."; then
    printf '%s' "$OLD" | while IFS= read -r d; do
      case "$d" in
        *"(program files of version 1.18)") rm -rf "$DATA/$NAME" "$DATA/_internal" "$DATA/icon.png" ;;
        *.AppImage) rm -f "$d" ;;
        *) rm -rf "$d" ;;
      esac
    done
    echo "Removed."
  fi
fi

if [ -n "$DISPLAY$WAYLAND_DISPLAY" ]; then
  (cd "$HERE" && setsid "./$NAME" >/dev/null 2>&1 < /dev/null &)
  echo "Starting Flrig EMCOMM..."
fi
exit 0
