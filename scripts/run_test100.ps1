param([string]$Config = 'configs/test100_fast.json', [int]$GpuLayers = 30)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $python -m generator faces --config $Config
if ($LASTEXITCODE) { throw 'Face generation failed; completed originals are preserved.' }
$configData = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
if ($configData.profiles.mode -eq 'local') {
    foreach ($stage in @('profiles','export','validate','package','preview')) {
        & $python -m generator $stage --config $Config
        if ($LASTEXITCODE) { throw "Stage failed: $stage" }
    }
    exit 0
}
$qwenProcess = $null
try {
    $healthy = $false
    try { $healthy = (Invoke-RestMethod 'http://127.0.0.1:8765/health' -TimeoutSec 2).status -eq 'ok' } catch {}
    if (!$healthy) {
        New-Item -ItemType Directory -Path 'work\logs' -Force | Out-Null
        $server = Join-Path $projectRoot 'tools\llama\llama-server.exe'
        $model = Join-Path $projectRoot 'models\qwen\Qwen3-14B-Q6_K.gguf'
        $qwenProcess = Start-Process -FilePath $server -ArgumentList @('-m',('"' + $model + '"'),'--alias','Qwen3-14B-Q6_K.gguf','--host','127.0.0.1','--port','8765','-ngl',$GpuLayers,'-c','4096','-np','1','-fa','on','--jinja','--reasoning-format','none') -WindowStyle Hidden -PassThru -RedirectStandardOutput 'work\logs\qwen-stdout.log' -RedirectStandardError 'work\logs\qwen-stderr.log'
        for ($attempt = 0; $attempt -lt 120; $attempt++) {
            try { $healthy = (Invoke-RestMethod 'http://127.0.0.1:8765/health' -TimeoutSec 2).status -eq 'ok' } catch {}
            if ($healthy) { break }
            if ($qwenProcess.HasExited) { throw 'Qwen exited. Check work/logs.' }
            Start-Sleep -Seconds 2
        }
        if (!$healthy) { throw 'Qwen did not become ready. Check work/logs.' }
    }
    foreach ($stage in @('profiles','export','validate','package','preview')) {
        & $python -m generator $stage --config $Config
        if ($LASTEXITCODE) { throw "Stage failed: $stage" }
    }
} finally {
    # Only stop the server spawned by this invocation, never an existing user server.
    if ($null -ne $qwenProcess -and !$qwenProcess.HasExited) {
        Stop-Process -Id $qwenProcess.Id -ErrorAction SilentlyContinue
    }
}
