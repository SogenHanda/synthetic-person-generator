param([int]$GpuLayers = 30, [int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$server = Join-Path $projectRoot 'tools\llama\llama-server.exe'
$model = Join-Path $projectRoot 'models\qwen\Qwen3-14B-Q6_K.gguf'
if (!(Test-Path -LiteralPath $model)) { throw 'Download assets first.' }
& $server -m $model --alias Qwen3-14B-Q6_K.gguf --host 127.0.0.1 --port $Port -ngl $GpuLayers -c 4096 -np 1 -fa on --jinja --reasoning-format none
exit $LASTEXITCODE
