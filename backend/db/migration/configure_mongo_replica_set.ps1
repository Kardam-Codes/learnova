param([Parameter(Mandatory=$true)][string]$BackupDirectory)
$ErrorActionPreference = 'Stop'
$configPath = 'C:\Program Files\MongoDB\Server\8.3\bin\mongod.cfg'
$backupPath = (Resolve-Path -LiteralPath $BackupDirectory).Path
$manifest = Get-Content -LiteralPath (Join-Path $backupPath 'manifest.json') -Raw | ConvertFrom-Json
foreach ($fileName in @('mongodb.archive.gz', 'mongod.original.cfg', 'mongod.replica-set.cfg')) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $backupPath $fileName) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $manifest.files.$fileName) { throw "Backup checksum mismatch: $fileName" }
}
$current = (Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($current -ne $manifest.files.'mongod.original.cfg') { throw 'Service configuration changed since backup; review it first.' }
$desired = [IO.File]::ReadAllText((Join-Path $backupPath 'mongod.replica-set.cfg'))
$configurationWritten = $false
Start-Transcript -Path (Join-Path $backupPath 'service-reconfiguration.log') -Append | Out-Null
try {
    [IO.File]::WriteAllText($configPath, $desired, (New-Object Text.UTF8Encoding($false)))
    $configurationWritten = $true
    Restart-Service -Name MongoDB
    (Get-Service MongoDB).WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
    'MongoDB service restarted with learnova-rs configuration. Replica-set initiation is the next explicit step.'
} catch {
    if ($configurationWritten) {
        Copy-Item -LiteralPath (Join-Path $backupPath 'mongod.original.cfg') -Destination $configPath -Force
        Start-Service -Name MongoDB -ErrorAction SilentlyContinue
    }
    throw
} finally {
    Stop-Transcript | Out-Null
}
