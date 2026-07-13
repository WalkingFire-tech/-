$max = 60
$i = 0
while ($i -lt $max) {
    try {
        $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/health' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Start-Process 'http://localhost:8000/'
            break
        }
    } catch {
    }
    Start-Sleep -Seconds 2
    $i += 2
}