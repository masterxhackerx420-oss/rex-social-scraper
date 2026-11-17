#!/bin/sh
# Rex's Social Scraper — Linux. User install, no root.
set -eu
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
root=$here
[ -f "$root/rex_social_scraper.py" ] || root=$here/..
[ -f "$root/rex_social_scraper.py" ] || { echo "rex_social_scraper.py is not next to this installer" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3.9 or newer is required." >&2; exit 1; }
mkdir -p "$HOME/.local/bin"
cp "$root/rex_social_scraper.py" "$HOME/.local/bin/rex-social-scraper"
chmod 755 "$HOME/.local/bin/rex-social-scraper"
echo "Installed $HOME/.local/bin/rex-social-scraper"
echo "Run: rex-social-scraper --platform bluesky,reddit,mastodon --query python --limit 10"
echo "If the command is not found, add \$HOME/.local/bin to PATH."
