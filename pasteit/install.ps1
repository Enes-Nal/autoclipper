# install.ps1
# Run once (no admin needed for per-user install)
# Usage: .\install.ps1          — install
#        .\install.ps1 -Uninstall — remove

param([switch]$Uninstall)

$extensionId  = "com.pasteit.premiere"
$extensionDir = "$env:APPDATA\Adobe\CEP\extensions\$extensionId"
$sourceDir    = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Uninstall) {
  if (Test-Path $extensionDir) { Remove-Item $extensionDir -Recurse -Force }
  Write-Output "Uninstalled. Restart Premiere Pro."
  exit 0
}

# Enable PlayerDebugMode for CEP 9–11
foreach ($v in @("CSXS.9", "CSXS.10", "CSXS.11")) {
  $key = "HKCU:\Software\Adobe\$v"
  if (!(Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
  Set-ItemProperty -Path $key -Name "PlayerDebugMode" -Value "1" -Type String
}
Write-Output "CEP debug mode enabled."

# Create extensions parent dir if needed
$parent = "$env:APPDATA\Adobe\CEP\extensions"
if (!(Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }

# Remove any existing link/dir
if (Test-Path $extensionDir) { Remove-Item $extensionDir -Recurse -Force }

# Junction works without admin on Windows
New-Item -ItemType Junction -Path $extensionDir -Target $sourceDir | Out-Null

Write-Output "Linked: $extensionDir"
Write-Output "  -> $sourceDir"
Write-Output ""
Write-Output "Restart Premiere Pro, then: Window > Extensions > PasteIt"
