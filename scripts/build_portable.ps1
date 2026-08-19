[CmdletBinding()]
param(
    [string]$Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonPath = Join-Path $ProjectRoot $Python
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "Python environment not found: $PythonPath"
}
$PythonBits = (& $PythonPath -c 'import struct; print(struct.calcsize("P") * 8)').Trim()
$PythonMachine = (& $PythonPath -c 'import platform; print(platform.machine())').Trim()
if ($LASTEXITCODE -ne 0 -or $PythonBits -ne "64" -or $PythonMachine -notin @("AMD64", "x86_64")) {
    throw "Windows x64 package requires a 64-bit x86 Python runtime; found $PythonMachine/$PythonBits-bit"
}

$WorkRoot = Join-Path $ProjectRoot "work\portable"
$DistRoot = Join-Path $WorkRoot "dist"
$BuildRoot = Join-Path $WorkRoot "build"
$SpecRoot = Join-Path $WorkRoot "spec"
$OutputRoot = Join-Path $ProjectRoot "outputs"
New-Item -ItemType Directory -Force -Path $WorkRoot, $DistRoot, $BuildRoot, $SpecRoot, $OutputRoot | Out-Null

$RequirementsJson = & $PythonPath -c 'import json,pathlib,sys,tomllib; data=tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); print(json.dumps(data["project"]["dependencies"] + data["project"]["optional-dependencies"]["release"]))' (Join-Path $ProjectRoot "pyproject.toml")
if ($LASTEXITCODE -ne 0) { throw "Failed to read dependencies from pyproject.toml" }
[string[]]$Requirements = $RequirementsJson | ConvertFrom-Json
& $PythonPath -m pip install @Requirements
if ($LASTEXITCODE -ne 0) { throw "Failed to install runtime and release dependencies" }

& $PythonPath -m PyInstaller `
    --noconfirm `
    --onedir `
    --name "JobAgent" `
    --paths (Join-Path $ProjectRoot "src") `
    --add-data "$(Join-Path $ProjectRoot 'src\job_agent\static');job_agent\static" `
    --add-data "$(Join-Path $ProjectRoot 'config.example.json');." `
    --distpath $DistRoot `
    --workpath $BuildRoot `
    --specpath $SpecRoot `
    (Join-Path $ProjectRoot "src\job_agent\launcher.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

$PackageRoot = Join-Path $DistRoot "JobAgent"
Copy-Item -LiteralPath (Join-Path $ProjectRoot "README.md") -Destination $PackageRoot
Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE") -Destination $PackageRoot
Copy-Item -LiteralPath (Join-Path $ProjectRoot "THIRD_PARTY_NOTICES.md") -Destination $PackageRoot
Copy-Item -LiteralPath (Join-Path $ProjectRoot "docs") -Destination $PackageRoot -Recurse

$Archive = Join-Path $OutputRoot "JobAgent-windows-x64.zip"
if (Test-Path -LiteralPath $Archive -PathType Leaf) {
    Remove-Item -LiteralPath $Archive
}
Compress-Archive -Path (Join-Path $PackageRoot "*") -DestinationPath $Archive -CompressionLevel Optimal
Write-Host "Portable package created: $Archive"
