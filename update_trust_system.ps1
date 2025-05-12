# PowerShell script to update the Twitter Trust System with real Twitter data
# This script collects trust assignments from Twitter, calculates trust scores, and pushes to GitHub

# Debug: Log environment info for scheduled task troubleshooting
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
"PATH: $env:PATH" | Out-File -FilePath "$scriptPath\env_log.txt" -Append
python --version | Out-File -FilePath "$scriptPath\env_log.txt" -Append
git --version | Out-File -FilePath "$scriptPath\env_log.txt" -Append

try {
    # Record that the script started
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    "Script started at $timestamp" | Out-File -FilePath "$scriptPath\latest_update.log" -Force

    # Set working directory to script location
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $scriptDir

    # Create a timestamp for this run
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $logFolder = "logs"
    $collectionLog = "twitter_collection.log"
    $calculationLog = "trust_calculation.log"
    $mainLog = "logs\update_$timestamp.log"

    # Create logs directory if it doesn't exist
    if (-not (Test-Path -Path $logFolder)) {
        New-Item -ItemType Directory -Path $logFolder | Out-Null
    }

    # Load configuration
    function Load-Config {
        $configPath = "config.json"
        if (Test-Path $configPath) {
            $config = Get-Content -Path $configPath -Raw | ConvertFrom-Json
            return $config
        } else {
            # Default configuration
            $config = @{
                update_frequency_minutes = 10
                api_settings = @{
                    host = "twitter-api45.p.rapidapi.com"
                    key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
                    search_query = "#ufotrust"
                    max_pages = 3
                }
                collection_settings = @{
                    tweet_lookback_minutes = 15
                    delay_between_requests = 2
                }
                trust_calculation = @{
                    rating_range = @{
                        min = -100
                        max = 100
                    }
                    normalization = "l2"
                    alpha = 0.85
                }
            }
            
            # Save default configuration
            $config | ConvertTo-Json -Depth 4 | Set-Content -Path $configPath
            return $config
        }
    }

    # Function to log messages
    function Write-Log {
        param (
            [string]$Message,
            [string]$Color = "White"
        )
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $logMessage = "[$timestamp] $Message"
        
        # Output to console with color
        Write-Host $logMessage -ForegroundColor $Color
        
        # Write to log file
        Add-Content -Path $mainLog -Value $logMessage
    }

    # Load configuration
    $config = Load-Config
    $updateFrequency = $config.update_frequency_minutes

    Write-Log "Starting Twitter Trust System update process..." "Green"
    Write-Log "Update frequency set to: $updateFrequency minutes" "Cyan"

    # Step 1: Collect trust assignments from Twitter
    Write-Log "Collecting trust assignments from Twitter..." "Yellow"
    & "C:\\Users\\Brian\\anaconda3\\Scripts\\conda.exe" run --no-capture-output -n trust python scripts/collect_trust.py

    # Check if the collection was successful by checking if file exists and was modified recently
    if (-not (Test-Path -Path "trust_assignments.json")) {
        Write-Log "Error: No trust assignments file found" "Red"
        exit 1
    }

    $fileInfo = Get-Item "trust_assignments.json"
    $fileAge = (Get-Date) - $fileInfo.LastWriteTime
    if ($fileAge.TotalMinutes -gt ($updateFrequency * 2)) {
        Write-Log "Warning: Trust assignments file not updated recently (last modified $($fileInfo.LastWriteTime))" "Yellow"
    }

    # Copy the collection log to our logs folder
    if (Test-Path -Path $collectionLog) {
        Copy-Item -Path $collectionLog -Destination "$logFolder\collection_$timestamp.log" -Force
        Add-Content -Path $mainLog -Value (Get-Content -Path $collectionLog)
    }

    # Step 2: Calculate trust scores
    Write-Log "Calculating trust scores from collected data..." "Yellow"
    & "C:\\Users\\Brian\\anaconda3\\Scripts\\conda.exe" run --no-capture-output -n trust python scripts/calculate_trust.py
    $calcExitCode = $LASTEXITCODE

    # Copy the calculation log to our logs folder
    if (Test-Path -Path $calculationLog) {
        Copy-Item -Path $calculationLog -Destination "$logFolder\calculation_$timestamp.log" -Force
        Add-Content -Path $mainLog -Value (Get-Content -Path $calculationLog)
    }

    # Check if calculation was successful
    if ($calcExitCode -ne 0 -or -not (Test-Path -Path "js/data.js")) {
        Write-Log "Error: Failed to generate data.js file" "Red"
        exit 1
    }

    # Get the last update time
    $lastUpdated = Get-Date -Format "MMMM d, yyyy h:mm tt"

    # Step 3: Commit and push changes to GitHub
    Write-Log "Committing and pushing changes to GitHub..." "Yellow"

    try {
        # Add the updated files
        git add js/data.js
        
        # Add the trust assignments file too (to keep history)
        if (Test-Path -Path "trust_assignments.json") {
            git add trust_assignments.json
        }
        
        # Add log files
        git add "logs/collection_$timestamp.log" 
        git add "logs/calculation_$timestamp.log"
        git add "logs/update_$timestamp.log"
        
        # Get statistics for commit message
        $assignmentsJson = Get-Content -Path "trust_assignments.json" -Raw | ConvertFrom-Json
        $totalRelationships = 0
        
        # Safely count relationships
        foreach ($source in $assignmentsJson.assignments.PSObject.Properties) {
            $count = $source.Value.Count
            $totalRelationships += $count
        }
        
        # Commit with detailed message
        git commit -m "Update trust data: $lastUpdated

Stats:
- $(($assignmentsJson.assignments.PSObject.Properties | Measure-Object).Count) users in network
- $totalRelationships trust relationships
- Updated every $updateFrequency minutes"
        
        # Push to GitHub
        git push origin main
        
        Write-Log "Successfully updated the trust system!" "Green"
        Write-Log "Website will be updated at https://github.com/UFOtwittertrust/ufotwittertrust/" "Green"
    } catch {
        Write-Log "Error: Failed to push changes to GitHub" "Red"
        Write-Log $_.Exception.Message "Red"
        exit 1
    }

    Write-Log "Trust system update completed with $totalRelationships total trust relationships" "Green"

    # Provide instructions for users to participate
    Write-Log "" "White"
    Write-Log "To participate in the trust system, users should tweet:" "Cyan"
    Write-Log "#ufotrust @username +70" "Yellow"
    Write-Log "or" "Cyan"
    Write-Log "#ufotrust @username -30" "Yellow"
    Write-Log "" "White"
    Write-Log "The system will be updated every $updateFrequency minutes with new trust assignments." "Cyan"

    # Copy logs to root directory for easy review
    Copy-Item -Path $mainLog -Destination "latest_update.log" -Force

    "Update completed at $(Get-Date)" | Out-File -FilePath "C:\Users\Brian\Downloads\trust\twitter-trust-system\trust_log.txt" -Append

    exit 0
} 
catch {
    # Log any errors
    "ERROR at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'): $($_.Exception.Message)" | Out-File -FilePath "$scriptPath\error_log.txt" -Append
}