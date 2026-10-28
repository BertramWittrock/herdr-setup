#!/bin/sh
# Set up this herdr config on a Mac: tools, keyboard lights, the Herdr launcher and the Warp tab.
# Run from the repo cloned to ~/.config/herdr. Safe to re-run after a git pull.
set -eu

repo=$(cd "$(dirname "$0")" && pwd)
[ "$repo" = "$HOME/.config/herdr" ] || { echo "Clone this repo to ~/.config/herdr first (herdr reads its config from there)." >&2; exit 1; }
[ "$(uname -s)" = Darwin ] || { echo "macOS only." >&2; exit 1; }
command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh" >&2; exit 1; }
xcode-select -p >/dev/null 2>&1 || { xcode-select --install; echo "Re-run install.sh once the Command Line Tools have installed." >&2; exit 1; }
PATH="$(brew --prefix)/bin:$PATH"

step() { printf '\n== %s\n' "$1"; }

step "Tools"
for formula in herdr jq python3; do
  command -v "$formula" >/dev/null || brew install "${formula%3}"
done
[ -d /Applications/Warp.app ] || brew install --cask warp

step "Keyboard lights"
git -C "$repo" submodule update --init keylights/librazermacos
"$repo/keylights/build.sh"
label=dk.celto.herdr-keylights
plist="$HOME/Library/LaunchAgents/$label.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat >"$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$label</string>
	<key>ProgramArguments</key>
	<array>
		<string>$(brew --prefix)/bin/python3</string>
		<string>-I</string>
		<string>$repo/keylights/keylights.py</string>
	</array>
	<key>EnvironmentVariables</key>
	<dict>
		<key>PATH</key>
		<string>$(brew --prefix)/bin:/usr/bin:/bin</string>
	</dict>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<true/>
	<key>StandardErrorPath</key>
	<string>$repo/keylights/keylights.log</string>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
while launchctl print "gui/$(id -u)/$label" >/dev/null 2>&1; do sleep 0.2; done  # bootstrap fails until it's gone
launchctl bootstrap "gui/$(id -u)" "$plist"
echo "started $label"

step "Warp tab and Herdr launcher"
mkdir -p "$HOME/.warp/tab_configs" "$HOME/Applications"
cp "$repo/warp/herdr.toml" "$HOME/.warp/tab_configs/herdr.toml"
app="$HOME/Applications/Herdr.app"
rm -rf "$app"
osacompile -o "$app" -e 'open location "warp://tab_config/herdr?new_window=true"'
plutil -replace CFBundleIdentifier -string dk.celto.herdr "$app/Contents/Info.plist"
plutil -replace LSUIElement -bool true "$app/Contents/Info.plist"
cp /Applications/Warp.app/Contents/Resources/AppIcon.icns "$app/Contents/Resources/applet.icns"
codesign --force --sign - "$app"
echo "built $app (type \"herdr\" in Spotlight or Raycast)"

step "Agent integrations"
for agent in claude codex opencode; do
  if command -v "$agent" >/dev/null; then
    herdr integration install "$agent"
  fi
done

step "herdr config"
herdr config check
if herdr status server 2>/dev/null | grep -q 'status: running'; then
  herdr server reload-config >/dev/null && echo "reloaded the running herdr"
fi

missing=""
for agent in claude cmd opencode codex; do
  command -v "$agent" >/dev/null || missing="$missing $agent"
done
if [ -n "$missing" ]; then
  step "Not installed (Shift+F7–F10 open these):$missing"
  echo "  claude:   curl -fsSL https://claude.ai/install.sh | bash"
  echo "  cmd:      npm i -g command-code"
  echo "  opencode: curl -fsSL https://opencode.ai/install | bash"
  echo "  codex:    npm i -g @openai/codex"
  echo "Then re-run install.sh to hook them into herdr."
fi
