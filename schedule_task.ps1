# PowerShell script to create or update the scheduled task for Twitter Trust System
# Run this with administrator privileges to set up automatic updates

# Get the script directory (full path)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$updateScriptPath = Join-Path -Path $scriptPath -ChildPath "update_trust_system.ps1"

# Load configuration to get update frequency
function Load-Config {
    $configPath = Join-Path -Path $scriptPath -ChildPath "config.json"
    if (Test-Path $configPath) {
        $config = Get-Content -Path $configPath -Raw | ConvertFrom-Json
        return $config
    } else {
        # Default configuration
        return @{
            update_frequency_minutes = 10
        }
    }
}

$config = Load-Config
$updateFrequency = $config.update_frequency_minutes

Write-Host "Setting up scheduled task to run every $updateFrequency minutes..." -ForegroundColor Green

# Check if task exists
$taskName = "TwitterTrustSystemUpdate"
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

# Create the action that will run the update script
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$updateScriptPath`"" -WorkingDirectory $scriptPath

# Set up trigger to run on schedule
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $updateFrequency) -RepetitionDuration ([TimeSpan]::MaxValue)

# Task settings
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Create or update the task
if ($taskExists) {
    # Update existing task
    Set-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings
    Write-Host "Updated scheduled task '$taskName' to run every $updateFrequency minutes." -ForegroundColor Green
} else {
    # Create new task
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Updates Twitter Trust System every $updateFrequency minutes"
    Write-Host "Created new scheduled task '$taskName' to run every $updateFrequency minutes." -ForegroundColor Green
}

# Show the task details
Get-ScheduledTask -TaskName $taskName | Format-List TaskName, TaskPath, State

Write-Host "`nTo change the update frequency:" -ForegroundColor Cyan
Write-Host "1. Edit config.json and update the 'update_frequency_minutes' value" -ForegroundColor Cyan
Write-Host "2. Run this script again to update the scheduled task" -ForegroundColor Cyan