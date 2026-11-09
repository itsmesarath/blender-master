# Install the blender-master skill into an agent's skills folder (Windows PowerShell).
#   .\install.ps1                  -> $HOME\.claude\skills\blender-master
#   .\install.ps1 -Cursor          -> .\.cursor\skills\blender-master (current project)
#   .\install.ps1 -Dir C:\path     -> C:\path\blender-master
#   add -Flat to also copy every sub-skill as its own top-level skill
param([switch]$Cursor, [string]$Dir = "", [switch]$Flat)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $HOME ".claude\skills"
if ($Cursor) { $dest = Join-Path (Get-Location) ".cursor\skills" }
if ($Dir -ne "") { $dest = $Dir }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$target = Join-Path $dest "blender-master"
if (Test-Path $target) {
    $backup = "$target.bak.$(Get-Date -Format yyyyMMddHHmmss)"
    Write-Host "existing install moved to $backup"
    Move-Item $target $backup
}
Copy-Item -Recurse (Join-Path $here "blender-master") $target
Get-ChildItem -Path $target -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
if ($Flat) {
    Get-ChildItem (Join-Path $target "subskills") -Directory | ForEach-Object {
        $link = Join-Path $dest $_.Name
        if (Test-Path $link) { Write-Host "skip $($_.Name) (exists)" }
        else { Copy-Item -Recurse $_.FullName $link }
    }
}
Write-Host "installed: $target"
