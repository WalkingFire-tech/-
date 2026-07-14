$max = 90
$i = 0
while ($i -lt $max) {
    try {
        $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/health' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            $json = $r.Content | ConvertFrom-Json
            if ($json.ready -eq $true) {
                Start-Process 'http://localhost:8000/'
                break
            }
            Write-Host "Waiting for server to finish initializing... ($i s)"
        }
    } catch {
        Write-Host "Server not reachable yet... ($i s)"
    }
    Start-Sleep -Seconds 3
    $i += 3
}
if ($i -ge $max) {
    Write-Host "Timeout: server did not become ready within $max seconds"
}
