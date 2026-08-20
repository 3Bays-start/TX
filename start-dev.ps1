# LX Platform 本地开发一键启动脚本
# 用法：右键 -> 使用 PowerShell 运行，或 powershell -ExecutionPolicy Bypass -File .\start-dev.ps1

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$LogDir = Join-Path $env:TEMP "lx_platform_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Start-Service {
    param(
        [string]$Title,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkDir,
        [string]$OutLog
    )
    $argStr = ($Arguments | ForEach-Object { $_ -replace ' ', '` ' }) -join ' '
    $ps = "`$env:PYTHONPATH='C:\Users\l1910\Desktop\TX\backend'; Start-Process -FilePath '$FilePath' -ArgumentList '$argStr' -WorkingDirectory '$WorkDir' -WindowStyle Minimized -RedirectStandardOutput '$OutLog' -RedirectStandardError '$OutLog.err'"
    Start-Process powershell.exe -WindowStyle Minimized -ArgumentList "-NoProfile","-Command",$ps
    Write-Host "启动 $Title ..."
}

Start-Service -Title "后端 Backend :8000" `
    -FilePath $VenvPy `
    -Arguments @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000") `
    -WorkDir (Join-Path $Root "backend") `
    -OutLog (Join-Path $LogDir "backend.log")

Start-Service -Title "用户端 Web :5174" `
    -FilePath "C:\Program Files\nodejs\npm.cmd" `
    -Arguments @("run","dev") `
    -WorkDir (Join-Path $Root "web") `
    -OutLog (Join-Path $LogDir "web.log")

Start-Service -Title "管理后台 Admin :5173" `
    -FilePath "C:\Program Files\nodejs\npm.cmd" `
    -Arguments @("run","dev") `
    -WorkDir (Join-Path $Root "admin") `
    -OutLog (Join-Path $LogDir "admin.log")

Write-Host ""
Write-Host "等待服务启动..."
Start-Sleep -Seconds 12

foreach ($pair in @(
    @{ Name = "后端 API   "; Url = "http://localhost:8000/health" },
    @{ Name = "用户端 Web "; Url = "http://localhost:5174/" },
    @{ Name = "管理后台   "; Url = "http://localhost:5173/admin/login" }
)) {
    try {
        $r = Invoke-WebRequest -Uri $pair.Url -TimeoutSec 5 -UseBasicParsing
        Write-Host ("{0} OK  {1}  ->  {2}" -f $pair.Name, $r.StatusCode, $pair.Url)
    } catch {
        Write-Host ("{0} FAIL {1}" -f $pair.Name, $pair.Url)
    }
}

Write-Host ""
Write-Host "访问地址："
Write-Host "  用户端    http://localhost:5174/"
Write-Host "  管理后台  http://localhost:5173/admin/login   (superadmin / Admin@123456)"
Write-Host "  API 文档  http://localhost:8000/docs"
Write-Host ""
Write-Host "停止服务：在对应的最小化窗口按 Ctrl+C，或结束对应进程。"