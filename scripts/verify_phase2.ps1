$ErrorActionPreference = "Stop"

Write-Host "[1/4] Python syntax check"
python -m compileall src | Out-Host

Write-Host "[2/4] Backend phase2 tests"
python -m unittest tests.test_import_service_phase2 tests.test_ladder_execution_flow | Out-Host

Write-Host "[3/4] Frontend type/build check"
Push-Location frontend
npm run build | Out-Host
Pop-Location

Write-Host "[4/4] Done"
