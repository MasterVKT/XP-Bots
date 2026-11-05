# Windows launcher for agent_lifecycle.py.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File .agents/hooks/invoke-agent-hook.ps1 -Mode <event>-<tool>
# The hook input is copied byte for byte from the raw standard input stream into a temporary file,
# then passed with --input-file: no PowerShell text pipeline ever touches it, so accents survive.
# Interpreter order: $env:XPBOTS_PYTHON, repository or parent .venv, py -3.13, python, python3.
# Fails open: without a compatible Python 3.13+, writes {} and exits 0.
param([Parameter(Mandatory = $true)][string]$Mode)

$hooksDir = $PSScriptRoot
$root = (Resolve-Path -ErrorAction Stop (Join-Path $hooksDir '..\..')).Path
$engine = Join-Path $hooksDir 'agent_lifecycle.py'
$stateDir = if ($env:XPBOTS_LIFECYCLE_STATE_DIR) { $env:XPBOTS_LIFECYCLE_STATE_DIR } else { Join-Path ([IO.Path]::GetTempPath()) 'xp-bots-agent-lifecycle' }

function Write-Neutral([string]$Reason) {
    try {
        New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
        Add-Content -Path (Join-Path $stateDir 'xp-bots-lifecycle-errors.log') -Encoding UTF8 -Value ("{0} launcher: {1} (mode {2})" -f ([DateTime]::UtcNow.ToString('o')), $Reason, $Mode)
    } catch { }
    [Console]::Out.Write('{}')
    exit 0
}

function Test-Python([string[]]$Command) {
    try {
        $exe = $Command[0]
        $rest = @()
        if ($Command.Length -gt 1) { $rest = $Command[1..($Command.Length - 1)] }
        & $exe @rest -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)' 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

$candidates = @()
if ($env:XPBOTS_PYTHON) { $candidates += , @($env:XPBOTS_PYTHON) }
foreach ($venv in @((Join-Path $root '.venv\Scripts\python.exe'), (Join-Path $root '..\.venv\Scripts\python.exe'))) {
    if (Test-Path $venv) { $candidates += , @($venv) }
}
if (Get-Command py -ErrorAction SilentlyContinue) { $candidates += , @('py', '-3.13') }
foreach ($name in @('python', 'python3')) {
    if (Get-Command $name -ErrorAction SilentlyContinue) { $candidates += , @($name) }
}

$python = $null
foreach ($candidate in $candidates) {
    if (Test-Python $candidate) { $python = $candidate; break }
}
if (-not $python) { Write-Neutral 'no Python 3.13+ interpreter found' }

$inputFile = Join-Path ([IO.Path]::GetTempPath()) ('xp-bots-hook-' + [Guid]::NewGuid().ToString('N') + '.json')
try {
    $source = [Console]::OpenStandardInput()
    $target = [IO.File]::Open($inputFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try { $source.CopyTo($target) } finally { $target.Dispose() }
} catch {
    Write-Neutral ('cannot copy hook input: ' + $_.Exception.Message)
}

$exe = $python[0]
$rest = @()
if ($python.Length -gt 1) { $rest = $python[1..($python.Length - 1)] }
$code = 0
try {
    # The engine writes one ASCII-only JSON object on stdout; it deletes the input file after reading.
    & $exe @rest -B $engine --mode $Mode --input-file $inputFile
    $code = $LASTEXITCODE
} catch {
    if (Test-Path $inputFile) { Remove-Item -Force $inputFile -ErrorAction SilentlyContinue }
    Write-Neutral ('engine launch failed: ' + $_.Exception.Message)
}
if (Test-Path $inputFile) { Remove-Item -Force $inputFile -ErrorAction SilentlyContinue }
exit $code
