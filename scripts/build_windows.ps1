$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

$python = Join-Path $projectRoot ".venv-build\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Build environment not found. Create .venv-build and install requirements-build.txt."
}

& $python scripts\run_isolated_test_suite.py
if ($LASTEXITCODE -ne 0) {
    throw "Tests failed. Package was not built."
}

& $python -m PyInstaller --noconfirm --clean Puma9980UI.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed."
}

& $python -m PyInstaller --noconfirm --clean Puma9980KeyGenerator.spec
if ($LASTEXITCODE -ne 0) {
    throw "Key generator PyInstaller build failed."
}

$exe = Join-Path $projectRoot "dist\Puma9980UI\Puma9980UI.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Expected executable was not created: $exe"
}
$keyGeneratorExe = Join-Path $projectRoot "dist\Puma9980KeyGenerator\Puma9980KeyGenerator.exe"
if (-not (Test-Path -LiteralPath $keyGeneratorExe)) {
    throw "Expected key generator executable was not created: $keyGeneratorExe"
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

$keyGeneratorArchive = Join-Path $releaseDir "Puma9980-KeyGenerator-Windows.zip"
Compress-Archive -LiteralPath (Join-Path $projectRoot "dist\Puma9980KeyGenerator") -DestinationPath $keyGeneratorArchive -Force

Write-Host "Executable: $exe"
Write-Host "Release archive: $archive"
Write-Host "Administrator key generator: $keyGeneratorExe"
Write-Host "Administrator archive: $keyGeneratorArchive"
