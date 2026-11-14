<#
.SYNOPSIS
    Toggle WebView2 remote debugging port (9229) for Apple Music UWP inspection.
.EXAMPLE
    .\enable_webview2_cdp.ps1 -Enable
    .\enable_webview2_cdp.ps1 -Disable
#>
param(
    [switch]$Enable,
    [switch]$Disable,
    [int]$Port = 9229
)

$regPath = "HKCU:\Environment"
$varName = "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"

if ($Disable -or (-not $Enable)) {
    Remove-ItemProperty -Path $regPath -Name $varName -ErrorAction SilentlyContinue
    Write-Host "Removed $varName from $regPath"
} else {
    $val = "--remote-debugging-port=$Port"
    Set-ItemProperty -Path $regPath -Name $varName -Value $val
    Write-Host "Set $varName=$val in $regPath"
}

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
$res = [UIntPtr]::Zero
[EnvBroadcast]::SendMessageTimeout([IntPtr]0xffff, 0x001A, [UIntPtr]::Zero, "Environment", 2, 2000, [ref]$res) | Out-Null
Write-Host "Broadcasted WM_SETTINGCHANGE. Restart AppleMusic.exe for changes to take effect."
