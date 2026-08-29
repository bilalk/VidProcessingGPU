# run_service.ps1 - keep the web service alive (relaunch on crash).
$PY = "C:\Users\tester\AppData\Local\Programs\Python\Python311\python.exe"
$APP = "C:\ReelFactoryWeb\app.py"
$LOG = "C:\ReelFactoryWeb\logs\service.log"
while ($true) {
    & $PY $APP *>> $LOG
    Start-Sleep -Seconds 5
}
