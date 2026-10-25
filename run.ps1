$ErrorActionPreference = 'Stop'
$settingsFile = Join-Path $PSScriptRoot 'local_environment.json'
if ($env:MECHANISM_PYTHON) {
    $runtimePython = $env:MECHANISM_PYTHON
} elseif (Test-Path -LiteralPath $settingsFile -PathType Leaf) {
    $runtimeSettings = Get-Content -LiteralPath $settingsFile -Raw | ConvertFrom-Json
    $runtimePython = $runtimeSettings.python
} else {
    throw 'Run scripts/configure_environment.py using the Python environment you intend to reuse, or set MECHANISM_PYTHON and MECHANISM_SW_INSTALL.'
}
if (-not (Test-Path -LiteralPath $runtimePython -PathType Leaf)) {
    throw 'Configured Python is missing. Run environment detection and set MECHANISM_PYTHON or update local_environment.json.'
}
$env:PYTHONUTF8 = '1'
$env:CADGEN_DAEMON = '0'
& $runtimePython (Join-Path $PSScriptRoot 'scripts\run_project.py') @args
exit $LASTEXITCODE
