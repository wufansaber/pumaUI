$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

$python = Join-Path $projectRoot ".venv-build\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Build environment not found. Create .venv-build and install requirements-build.txt."
}

& $python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) {
    throw "Tests failed. Package was not built."
}

& $python -m PyInstaller --noconfirm --clean Puma9980UI.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed."
}

$exe = Join-Path $projectRoot "dist\Puma9980UI\Puma9980UI.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Expected executable was not created: $exe"
}

$releaseDir = Join-Path $projectRoot "release"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
$archive = Join-Path $releaseDir "Puma9980UI-Windows.zip"
$archiveCreated = $false
for ($attempt = 1; $attempt -le 5; $attempt++) {
    try {
        Compress-Archive -LiteralPath (Join-Path $projectRoot "dist\Puma9980UI") -DestinationPath $archive -Force
        $archiveCreated = $true
        break
    }
    catch {
        if ($attempt -eq 5) {
            throw
        }
        Start-Sleep -Seconds 2
    }
}
if (-not $archiveCreated) {
    throw "Release archive was not created."
}

Write-Host "Executable: $exe"
Write-Host "Release archive: $archive"
