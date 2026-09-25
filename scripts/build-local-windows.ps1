param(
    [switch]$Clean,
    [switch]$SkipTests,
    [string]$Output = "release",
    [switch]$VerboseBuild
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv no está instalado. Instálalo desde https://docs.astral.sh/uv/ y vuelve a ejecutar este script."
}

$arguments = @("run", "--locked", "--group", "dev", "python", "scripts/build_local.py", "--output", $Output)
if ($Clean) { $arguments += "--clean" }
if ($SkipTests) { $arguments += "--skip-tests" }
if ($VerboseBuild) { $arguments += "--verbose" }
& uv @arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }