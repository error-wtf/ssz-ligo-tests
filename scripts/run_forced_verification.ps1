Set-Location E:\clone\ssz-ligo-tests
New-Item -ItemType Directory -Force -Path logs,reports,data_manifest | Out-Null
python scripts\forced_verify.py `
    1> logs\forced_verification_stdout.log `
    2> logs\forced_verification_stderr.log
$exitCode = $LASTEXITCODE
Write-Host "=== STDOUT (last 120 lines) ==="
Get-Content logs\forced_verification_stdout.log -Tail 120
Write-Host "=== STDERR (last 120 lines) ==="
Get-Content logs\forced_verification_stderr.log -Tail 120
Write-Host "=== EXIT CODE: $exitCode ==="
exit $exitCode
