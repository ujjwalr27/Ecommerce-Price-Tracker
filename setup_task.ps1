# PowerShell script to set up a Windows Scheduled Task for the price tracker
param (
    [string]$TaskName = "PriceTracker",
    [int]$IntervalHours = 1,
    [string]$RunBatPath = $null
)

# Get the current directory if bat path not provided
if (-not $RunBatPath) {
    $RunBatPath = Join-Path -Path $PSScriptRoot -ChildPath "run_tracker.bat"
}

# Ensure the path is absolute
$RunBatPath = Resolve-Path -Path $RunBatPath -ErrorAction SilentlyContinue
if (-not $RunBatPath) {
    Write-Error "Cannot find the run_tracker.bat file. Please provide the correct path."
    exit 1
}

Write-Host "Setting up Windows Scheduled Task for Price Tracker" -ForegroundColor Green
Write-Host "Task Name: $TaskName" -ForegroundColor Cyan
Write-Host "Interval: Every $IntervalHours hour(s)" -ForegroundColor Cyan
Write-Host "Script: $RunBatPath" -ForegroundColor Cyan

# Check if the task already exists
$taskExists = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($taskExists) {
    Write-Host "A task with the name '$TaskName' already exists." -ForegroundColor Yellow
    $confirmation = Read-Host "Do you want to replace it? (y/n)"
    if ($confirmation -ne 'y') {
        Write-Host "Task setup canceled." -ForegroundColor Red
        exit 0
    }
    
    # Remove the existing task
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Existing task removed." -ForegroundColor Yellow
}

# Create a trigger that runs every X hours
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)

# Create an action to run the batch file
$action = New-ScheduledTaskAction -Execute $RunBatPath -WorkingDirectory (Split-Path -Parent $RunBatPath)

# Set principal to run with highest privileges
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Highest

# Create the task settings
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Register the task
Register-ScheduledTask -TaskName $TaskName -Trigger $trigger -Action $action -Principal $principal -Settings $settings

Write-Host "Task '$TaskName' has been created successfully!" -ForegroundColor Green
Write-Host "The price tracker will run every $IntervalHours hour(s)." -ForegroundColor Green
Write-Host "Note: You can manage your scheduled tasks in Task Scheduler (taskschd.msc)." -ForegroundColor Cyan 