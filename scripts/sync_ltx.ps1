# sync_ltx.ps1 - continuously pull newly-completed reels from the GPU server to the
# host PC over HTTP (reliable under GPU load, unlike ssh), and report back to the
# status page how many reels are now on the host via /settransferred.
param([int]$IntervalSec = 60, [switch]$Once)

$BASE = 'http://129.212.190.223'
$LM   = 'C:\ProjectComfy\reelsGPU2\ltx_29aug_mobile'
$LD   = 'C:\ProjectComfy\reelsGPU2\ltx_29aug_desktop'
$LOGF = 'C:\ProjectComfy\reelsGPU2\sync_ltx.log'
$MAX  = 24

function Log($m) {
    $t = (Get-Date).ToString('s')
    Add-Content -Path $LOGF -Value "$t  $m"
}

function Get-Copied {
    $mm = @(Get-ChildItem -Recurse $LM -Filter *.mp4 -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    $dd = @(Get-ChildItem -Recurse $LD -Filter *.mp4 -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    return @($mm | Where-Object { $dd -contains $_ }).Count
}

while ($true) {
    $done = 0
    try {
        $api = (Invoke-WebRequest -Uri "$BASE/api" -TimeoutSec 20 -UseBasicParsing).Content | ConvertFrom-Json
        if ($api.sum -match 'Completed:\s*(\d+)') { $done = [int]$Matches[1] }
        $files = (Invoke-WebRequest -Uri "$BASE/list" -TimeoutSec 20 -UseBasicParsing).Content | ConvertFrom-Json
        if ($null -eq $files) { $files = @() }
    } catch {
        Log "list/api ERR: $($_.Exception.Message)"
        if ($Once) { break }
        Start-Sleep -Seconds $IntervalSec; continue
    }

    $pulled = 0
    $failed = @()
    foreach ($f in $files) {
        $kind = $f.kind
        $rel  = $f.rel
        $local = if ($kind -eq 'mobile') { Join-Path $LM ($rel.Replace('/', '\')) } else { Join-Path $LD ($rel.Replace('/', '\')) }
        if (Test-Path $local) { continue }
        $dir = Split-Path $local
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        try {
            Invoke-WebRequest -Uri "$BASE/file/$kind/$rel" -OutFile $local -TimeoutSec 600 -UseBasicParsing
            if ((Test-Path $local) -and ((Get-Item $local).Length -gt 0)) {
                $pulled++
                $c = Get-Copied
                try { Invoke-WebRequest -Uri "$BASE/settransferred?n=$c" -TimeoutSec 15 -UseBasicParsing | Out-Null } catch {}
            } else {
                $failed += $rel
                Remove-Item $local -Force -ErrorAction SilentlyContinue
            }
        } catch {
            $failed += $rel
            Remove-Item $local -Force -ErrorAction SilentlyContinue
        }
    }

    $transferred = Get-Copied
    try { Invoke-WebRequest -Uri "$BASE/settransferred?n=$transferred" -TimeoutSec 15 -UseBasicParsing | Out-Null } catch {}

    Log "sync: new-pulled=$pulled  on-host=$transferred  completed=$done  failures=$($failed.Count)"
    if ($failed.Count -gt 0) { Log "  FAILED: $($failed -join ', ')" }
    if ($Once -or ($done -ge $MAX -and $failed.Count -eq 0)) { Log "cycle done (completed=$done/$MAX)"; break }
    Start-Sleep -Seconds $IntervalSec
}
