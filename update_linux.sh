#!/bin/bash
# ------------------------------------------------------------------
#  Flrig EMCOMM - update on Linux from the newest flrig-emcomm*.zip in ~/Downloads.
#  Run:   bash ~/flrig-emcomm/update_linux.sh
#  Unpacks a fresh copy of the code into ~/flrig-emcomm, then builds, installs
#  and starts it (linux_install.sh). Your station list is never touched.
# ------------------------------------------------------------------
set -e
ZIP=$(ls -t "$HOME"/Downloads/flrig-emcomm*.zip 2>/dev/null | head -1)
[ -n "$ZIP" ] || { echo "No flrig-emcomm*.zip in ~/Downloads"; exit 1; }
SRC="$HOME/flrig-emcomm"
KEEP="$HOME/.flrig-emcomm_update_keep"
echo "Using: $ZIP"

pkill -x FlrigEMCOMM 2>/dev/null && sleep 1 || true

# Unpack to a temporary folder first, so a bad zip leaves the old code in place
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"
NEW=$(dirname "$(find "$TMP" -maxdepth 3 -name linux_install.sh | head -1)")
[ -f "$NEW/linux_install.sh" ] || { echo "That zip doesn't look like Flrig EMCOMM"; exit 1; }

# Keep the build tools (saves re-downloading them) and any list kept with the code
rm -rf "$KEEP"; mkdir -p "$KEEP"
if [ -d "$SRC/.buildenv" ]; then mv "$SRC/.buildenv" "$KEEP/"; fi
for f in "$SRC"/flrig_stations.json*; do if [ -f "$f" ]; then mv "$f" "$KEEP/"; fi; done
rm -rf "$SRC"
mv "$NEW" "$SRC"
mv "$KEEP"/.buildenv "$SRC/" 2>/dev/null || true
for f in "$KEEP"/flrig_stations.json*; do if [ -f "$f" ]; then mv "$f" "$SRC/"; fi; done
rm -rf "$KEEP"

bash "$SRC/linux_install.sh"
