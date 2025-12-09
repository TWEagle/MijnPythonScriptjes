# ==========================================
# sync-pi.ps1 - Pure PowerShell + SSH/SCP
# ==========================================

$PiHost    = "192.168.111.205"
$PiUser    = "tweagle"
$PiPath    = "/home/tweagle/dns-scanner-webapp"
$LocalPath = "C:\gh\MijnPythonScriptjes\dsw"

# Logfile
$LogDir = "C:\gh\MijnPythonScriptjes\logs"
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir ("sync_pi_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
Start-Transcript -Path $LogFile -Force | Out-Null

Write-Host "=== CyNiT DNS Scanner SYNC ==="

# Zorg dat lokale map bestaat
if (!(Test-Path $LocalPath)) { New-Item -ItemType Directory -Path $LocalPath | Out-Null }

# 1. Haal bestandenlijst op zonder venv + zonder __pycache__
$ListCommand = "cd '$PiPath' ; find . -type f -not -path './venv/*' -not -path '*/__pycache__/*'"
$RemoteList = ssh "$PiUser@$PiHost" $ListCommand

if (!$RemoteList) {
    Write-Host "FOUT: kon geen lijst ophalen."
    Stop-Transcript | Out-Null
    exit
}

function Get-LocalEpoch($Path) {
    $info = Get-Item $Path
    return [int][double](($info.LastWriteTimeUtc - [DateTime]'1970-01-01').TotalSeconds)
}

foreach ($RemoteFile in $RemoteList) {

    $Relative = $RemoteFile.Trim().TrimStart('.', '/')
    if (!$Relative) { continue }

    $RemoteFull = "$PiPath/$Relative"
    $LocalFile = Join-Path $LocalPath $Relative
    $LocalDir  = Split-Path $LocalFile

    if (!(Test-Path $LocalDir)) {
        New-Item -ItemType Directory -Path $LocalDir -Force | Out-Null
    }

    $Download = $false

    if (!(Test-Path $LocalFile)) {
        $Download = $true
    } else {
        $RemoteTime = ssh "$PiUser@$PiHost" "stat -c %Y '$RemoteFull'" 2>$null
        if ($RemoteTime) {
            $LocalEpoch  = Get-LocalEpoch $LocalFile
            $RemoteEpoch = [int]$RemoteTime
            if ($RemoteEpoch -gt $LocalEpoch) { $Download = $true }
        } else {
            $Download = $true
        }
    }

    if ($Download) {
        Write-Host ("Downloading: {0}" -f $Relative)
        $RemoteSpec = ("{0}@{1}:'{2}'" -f $PiUser, $PiHost, $RemoteFull)
        scp $RemoteSpec "$LocalFile"
    } else {
        Write-Host ("Up-to-date:  {0}" -f $Relative)
    }
}

Write-Host "SYNC VOLTOOID"
Stop-Transcript | Out-Null
