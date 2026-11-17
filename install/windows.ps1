# Rex's Social Scraper — Windows. User install, no admin.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = $here
if (-not (Test-Path (Join-Path $root "rex_social_scraper.py"))) { $root = Split-Path -Parent $here }
$src = Join-Path $root "rex_social_scraper.py"
if (-not (Test-Path $src)) { throw "rex_social_scraper.py is not next to this installer" }
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { throw "Python 3.9 or newer is required. Install it from python.org, then run this again." }
$dest = Join-Path $env:LOCALAPPDATA "RexSocialScraper"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item $src (Join-Path $dest "rex_social_scraper.py") -Force
$cmd = Join-Path $dest "rex-social-scraper.cmd"
@"
@echo off
py -3 "%LOCALAPPDATA%\RexSocialScraper\rex_social_scraper.py" %*
"@ | Set-Content -Encoding ASCII $cmd
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$dest*") {
  [Environment]::SetEnvironmentVariable("Path", "$userPath;$dest", "User")
}
Write-Host "Installed $cmd"
Write-Host "Open a new terminal and run: rex-social-scraper --platform bluesky,reddit --query python --limit 10"
