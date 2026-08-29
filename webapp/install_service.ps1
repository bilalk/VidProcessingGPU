# install_service.ps1 - open port 5000 in firewall + register an auto-start task.
$ErrorActionPreference = 'Continue'

Write-Host "== 1. firewall rule for TCP 5000 =="
netsh advfirewall firewall delete rule name="ReelFactoryWeb 5000" 2>$null | Out-Null
netsh advfirewall firewall add rule name="ReelFactoryWeb 5000" dir=in action=allow protocol=TCP localport=5000

Write-Host "== 2. scheduled task (auto-start at boot, runs as SYSTEM) =="
schtasks /create /tn "ReelFactoryWeb" /f /sc onstart /ru SYSTEM /rl HIGHEST `
  /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\ReelFactoryWeb\run_service.ps1"

Write-Host "== 3. start it now =="
schtasks /run /tn "ReelFactoryWeb"
Start-Sleep -Seconds 5
schtasks /query /tn "ReelFactoryWeb" /fo LIST | Select-String "Status","Task Name","Run As"
