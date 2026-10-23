param([switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$runtime=Join-Path (Split-Path $repo) 'audit-runtime/laptop-prices-20261023'
if (!(Test-Path -LiteralPath (Join-Path $runtime 'demo-manifest.json'))) { throw 'Frozen manifest missing; no preparation is performed here.' }
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:8082'
$env:DEMO_PRESENTER='true'
$env:DEMO_PRESENTER_VERIFY=if ($VerifyOnly) {'true'} else {'false'}
$output=Join-Path $runtime ('presenter-native-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
Push-Location (Join-Path $repo 'v2\frontend')
try {
  # Existing runner validates environment, admin, manifest and document hashes.
  # Native viewport; does not start the tour, build, seed, reset or restore.
  npx.cmd playwright test e2e/demo-presenter.spec.ts --headed --workers=1 --output=$output --reporter=line
  if ($LASTEXITCODE -ne 0) { throw 'Presenter verification failed' }
} finally { Pop-Location }
