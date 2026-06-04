$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Renderer = Join-Path $Root ".venv\Scripts\juling-render.exe"

if (-not (Test-Path $Renderer)) {
  Write-Error "juling-render is not installed. Run: .\.venv\Scripts\python.exe -m pip install -e ."
  exit 1
}

& $Renderer @args
exit $LASTEXITCODE
