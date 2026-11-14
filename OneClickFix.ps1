<#
.SYNOPSIS
    Apple Music (Windows UWP) + UNiDAYS Student Verification One-Click Fix (v1.0.0)
    Apple Music (Windows 端) + UNiDAYS 学生验证无限跳转一键修复脚本 (v1.0.0)

.DESCRIPTION
    1. Enables WebView2 CDP remote debugging (--remote-debugging-port=9229) temporarily.
    2. Restarts AppleMusic.exe so the embedded finance-app WebView2 listens on 127.0.0.1:9229.
    3. Automatically captures `ud_s` from the `itmss://` UNiDAYS callback (or accepts `-UdS`).
    4. Binds `ud_s` via `updateUnidaysStatusSrv` (Ember.$.ajax) and triggers `startListening`
       on `route:music/subscribe` without broken `ud_h/ud_s/ud_t` parameters.
    5. Always cleans up temporary registry keys in `finally`.
#>
param(
    [ValidateSet("zh", "en", "")]
    [string]$Lang = "",
    [string]$UdS = "",
    [int]$Port = 9229
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$VERSION = "1.0.0"

if (-not $Lang) {
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host " Apple Music Windows + UNiDAYS One-Click Fix v$VERSION" -ForegroundColor Cyan
    Write-Host " Apple Music Windows 学生验证无限跳转一键修复工具 v$VERSION" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host " [1] 中文 (简体)  [Default]"
    Write-Host " [2] English"
    $choice = Read-Host "Select language / 请选择语言 (1/2)"
    if ($choice -eq "2") { $Lang = "en" } else { $Lang = "zh" }
}

$Msgs = @{
    zh = @{
        Banner      = "=== Apple Music + UNiDAYS 一键修复工具 v$VERSION ==="
        CheckPy     = "[1/5] 检查 Python 与 websocket-client 依赖..."
        EnableCdp   = "[2/5] 临时开启 WebView2 远程调试端口 (127.0.0.1:$Port) 并重启 Apple Music..."
        WaitAm      = "      请在打开的 Apple Music 客户端中进入【主页/立即试用 -> 选择大学生方案】页面。"
        HookItmss   = "[3/5] 正在设置临时 itmss:// 协议拦截器以自动捕获 UNiDAYS 回调 Token (ud_s)..."
        PromptUd    = "      👉 请在 Apple Music 中点击【验证资格 (Verify Eligibility)】并在浏览器完成 UNiDAYS 跳转；`n         或者直接在此粘贴含 ud_s= 的链接/Token（直接回车则进入自动等待捕获模式）"
        WaitingUd   = "      正在等待浏览器跳转 itmss:// 自动捕获 ud_s (最长等待 180 秒)..."
        CapturedUd  = "      ✅ 已成功捕获 ud_s Token！"
        RunBind     = "[4/5] 正在通过 WebView2 CDP 绑定学生资格并直接拉起大学生订阅结账..."
        CleanUp     = "[5/5] 正在清理临时环境变量与注册表项..."
        Done        = "✅ 修复流程执行完毕！请在 Apple Music 弹出的原生窗口中完成登录确认与支付验证。"
        ErrNoUd     = "❌ 未能获取有效的 ud_s Token，请确认已在浏览器完成 UNiDAYS 验证。"
    }
    en = @{
        Banner      = "=== Apple Music + UNiDAYS One-Click Fix v$VERSION ==="
        CheckPy     = "[1/5] Checking Python and websocket-client dependency..."
        EnableCdp   = "[2/5] Enabling temporary WebView2 CDP port (127.0.0.1:$Port) and restarting Apple Music..."
        WaitAm      = "      In Apple Music, please open the Subscription sheet and select 'University Student'."
        HookItmss   = "[3/5] Installing temporary itmss:// protocol hook to auto-capture UNiDAYS token (ud_s)..."
        PromptUd    = "      👉 Click 'Verify Eligibility' in Apple Music and complete the UNiDAYS browser redirect;`n         OR paste a URL/token containing ud_s= here (press Enter to auto-wait for redirect)"
        WaitingUd   = "      Waiting for browser itmss:// redirect to auto-capture ud_s (timeout: 180s)..."
        CapturedUd  = "      ✅ Successfully captured ud_s token!"
        RunBind     = "[4/5] Binding student status via WebView2 CDP and triggering direct student checkout..."
        CleanUp     = "[5/5] Cleaning up temporary environment variables and registry keys..."
        Done        = "✅ Fix completed! Please finish the native Apple Account sign-in and billing verification."
        ErrNoUd     = "❌ Failed to obtain a valid ud_s token. Please complete UNiDAYS verification in your browser."
    }
}[$Lang]

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class EnvBroadcast {
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern IntPtr SendMessageTimeout(
        IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam,
        uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
}
"@

function Broadcast-EnvChange {
    $res = [UIntPtr]::Zero
    [EnvBroadcast]::SendMessageTimeout([IntPtr]0xffff, 0x001A, [UIntPtr]::Zero, "Environment", 2, 2000, [ref]$res) | Out-Null
}

function Extract-UdS([string]$raw) {
    if (-not $raw) { return "" }
    $raw = $raw.Trim()
    if ($raw -match "ud_s=([^&\s]+)") {
        return [System.Uri]::UnescapeDataString($Matches[1])
    }
    return $raw
}

$capFile = Join-Path $env:TEMP "am_unidays_itmss_capture.txt"
$itmssReg = "HKCU:\Software\Classes\itmss\shell\open\command"

try {
    Write-Host "`n$($Msgs.Banner)" -ForegroundColor Green

    # 1. Check Python & websocket-client
    Write-Host $Msgs.CheckPy -ForegroundColor Yellow
    $pyCmd = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
    & $pyCmd -c "import websocket" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $pyCmd -m pip install websocket-client --quiet
    }

    # 2. Enable WebView2 CDP & restart AppleMusic.exe
    Write-Host $Msgs.EnableCdp -ForegroundColor Yellow
    Set-ItemProperty -Path "HKCU:\Environment" -Name "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS" -Value "--remote-debugging-port=$Port"
    Broadcast-EnvChange

    Get-Process -Name "AppleMusic","msedgewebview2" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Start-Process "shell:AppsFolder\AppleInc.AppleMusicWin_nzyj5cx40ttqa!App" -ErrorAction SilentlyContinue
    Write-Host $Msgs.WaitAm -ForegroundColor Cyan

    # 3. Obtain ud_s (either from parameter, user input, or automatic itmss:// hook)
    $token = Extract-UdS $UdS
    if (-not $token) {
        Write-Host $Msgs.HookItmss -ForegroundColor Yellow
        if (Test-Path $capFile) { Remove-Item $capFile -Force }
        New-Item -Path $itmssReg -Force | Out-Null
        $hookCmd = "powershell.exe -NoProfile -WindowStyle Hidden -Command `"Set-Content -Path '$capFile' -Value '%1' -Encoding UTF8`""
        Set-ItemProperty -Path $itmssReg -Name "(Default)" -Value $hookCmd

        $manual = Read-Host $Msgs.PromptUd
        if ($manual) {
            $token = Extract-UdS $manual
        } else {
            Write-Host $Msgs.WaitingUd -ForegroundColor Cyan
            $deadline = (Get-Date).AddSeconds(180)
            while ((Get-Date) -lt $deadline) {
                if (Test-Path $capFile) {
                    $rawUrl = Get-Content $capFile -Raw -ErrorAction SilentlyContinue
                    $token = Extract-UdS $rawUrl
                    if ($token) { break }
                }
                Start-Sleep -Milliseconds 500
            }
        }
        Remove-Item -Path "HKCU:\Software\Classes\itmss\shell" -Recurse -Force -ErrorAction SilentlyContinue
    }

    if (-not $token) {
        Write-Host $Msgs.ErrNoUd -ForegroundColor Red
        exit 1
    }
    Write-Host $Msgs.CapturedUd -ForegroundColor Green

    # 4. Bind UNiDAYS status & trigger student checkout via CDP
    Write-Host $Msgs.RunBind -ForegroundColor Yellow
    $pyScript = Join-Path $PSScriptRoot "scripts\bind_unidays_and_checkout.py"
    & $pyCmd $pyScript --ud-s "$token" --port $Port --lang $Lang --checkout
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Host "`n$($Msgs.Done)" -ForegroundColor Green
} finally {
    Write-Host $Msgs.CleanUp -ForegroundColor DarkGray
    Remove-ItemProperty -Path "HKCU:\Environment" -Name "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS" -ErrorAction SilentlyContinue
    Remove-Item -Path "HKCU:\Software\Classes\itmss\shell" -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $capFile) { Remove-Item $capFile -Force -ErrorAction SilentlyContinue }
    Broadcast-EnvChange
}
