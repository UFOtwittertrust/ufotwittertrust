# Simple test script to verify scheduled tasks are working
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logPath = "C:\Users\Brian\Downloads\trust\twitter-trust-system\task_test_log.txt"
"Task executed at $timestamp" | Out-File -FilePath $logPath -Append
"# Current working directory: $(Get-Location)" | Out-File -FilePath $logPath -Append
