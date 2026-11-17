#!/data/data/com.termux/files/usr/bin/bash
# Rex's Social Scraper — Android via Termux.
# The home-screen app is the live page: Chrome menu, Install app / Add to Home screen.
set -eu
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
root=$here
[ -f "$root/rex_social_scraper.py" ] || root=$here/..
[ -f "$root/rex_social_scraper.py" ] || { echo "rex_social_scraper.py is not next to this installer" >&2; exit 1; }
if ! command -v python3 >/dev/null 2>&1; then
  if command -v pkg >/dev/null 2>&1; then
    pkg install -y python
  else
    echo "Install Termux, then run this script again." >&2
    exit 1
  fi
fi
mkdir -p "$PREFIX/bin"
cp "$root/rex_social_scraper.py" "$PREFIX/bin/rex-social-scraper"
chmod 755 "$PREFIX/bin/rex-social-scraper"
echo "Installed rex-social-scraper"
echo "Live app: https://rexs-social-scraper-wolfsec.grok.me/"
echo "Run: rex-social-scraper --platform bluesky,mastodon --query python --limit 10"
