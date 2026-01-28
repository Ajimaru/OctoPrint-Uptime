<#
  PowerShell helper to open Git for Windows download page.
  Optionally extend this script to download+run the installer interactively.
#>

param(
    [switch]$OpenOnly
)

$url = 'https://git-scm.com/download/win'

try {
    Start-Process -FilePath $url
    Write-Output "Opened download page: $url"
} catch {
    Write-Error "Failed to open browser. Please open this URL manually: $url"
}

if (-not $OpenOnly) {
    Write-Output "If you want the installer downloaded automatically, re-run this script with -OpenOnly removed and implement a download step."
}
