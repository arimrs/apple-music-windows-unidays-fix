# Apple Music Windows + UNiDAYS Student Verification Infinite Redirect One-Click Fix

**[🇨🇳 简体中文](README.zh-CN.md) | 🇺🇸 English**

[![Release](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows)](https://www.microsoft.com/windows)
[![App](https://img.shields.io/badge/Client-Apple%20Music%20UWP-FA243C?logo=applemusic)](https://apps.microsoft.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> This tool provides a temporary workaround for the bug where **Apple Music on Windows (`AppleMusic.exe`) gets stuck in an infinite redirect loop and fails to complete student subscription even after passing UNiDAYS verification**. The issue has been reported to Apple awaiting an official fix. This project is completely free and open-source for technical troubleshooting and educational purposes only — **it does NOT bypass student eligibility checks or payment requirements**, and is strictly non-commercial.

---

Please note that this issue is not caused by transient network glitches or account anomalies. Instead, it is an inevitable result of **a frontend logic defect in Apple's `finance-app` bundle** combined with **missing protocol parameter forwarding in the Windows UWP client (`AppxManifest.xml`)**, making it consistently reproducible across all Windows 10/11 installations:

1. **Frontend Template Ignores Verified Status (`finance-app/templates/music/subscribe`, line 191)**:
   - The template controls the primary CTA button via `["block", "unless", [["get", "isStudentOfferSelected"]]]`: whenever the **University Student** plan (`salableAdamId: 1608221191`) is selected, the button unconditionally renders **"Verify Eligibility"** (`action: "verifyEligibility"`), completely ignoring the existing `isVerifiedStudent` (`userInfo.isStudent === true`) state in `service:music-subscription`.
2. **Windows UWP Client Drops `itmss://` Deep-Link Callback Parameters**:
   - Clicking "Verify Eligibility" calls `verifyWithUnidays("studentSubscriptionOffersiTunes")`, launching the browser to UNiDAYS and redirecting back to:
     `itmss://itunes.apple.com/studentSubscriptionOffers?app=music&ud_h=...&ud_s=...&ud_t=...`
   - While `AppleMusic.exe` on Windows registers the `itmss://` scheme in `AppxManifest.xml`, activating it **only brings the main window to the foreground without forwarding the `studentSubscriptionOffers` route or `(ud_h, ud_s, ud_t)` parameters to the embedded WebView2 (`finance-app`)**, resulting in an endless loop back to the initial screen.
3. **Backend Rejection on Manual Deep-Link Replay + `404` on Web Fallback**:
   - Forcing WebView2 to navigate directly to `studentSubscriptionOffers` with `(ud_h, ud_s, ud_t)` causes `MZBuy.woa/wa/buyProduct` to fail with `"You could not be verified as a university student. Contact UNiDAYS® for support."`
   - Clicking "Accept Offer / Free Trial" from the UNiDAYS web page or Apple Music Web Player redirects to `https://itunes.apple.com/subscribe?app=music`, which directly returns **`404 Not Found`**.

### How Does It Work?

1. **Automatically Intercept & Extract `ud_s`**: By registering a temporary `HKCU\Software\Classes\itmss` protocol hook, the script automatically captures the `ud_s` token when your browser finishes UNiDAYS verification and redirects back via `itmss://` (the registry key is removed immediately after capture — no manual packet sniffing required).
2. **Bind Student Status via the Internal Ember Container & `Ember.$.ajax`**:
   - Connects to the embedded WebView2 CDP port (`127.0.0.1:9229`) of `AppleMusic.exe` and locates the live Ember container `Ember.Namespace.NAMESPACES.find(n => n && n.__container__)`.
   - Reads `updateUnidaysStatusSrv` (`https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus`) from `service:itunes-bag` and sends `POST {"ud_s": "<TOKEN>"}` via **`Ember.$.ajax`** (which automatically triggers `Ember.$.ajaxPrefilter` to inject the client's native `X-Apple-Store-Front`, `X-Dsid`, and `X-Token` authentication headers), returning `HTTP 200` with `{"status": 0}`.
3. **Trigger Native Checkout Directly on a Clean `/music/subscribe` Route**:
   - Strips the problematic `ud_h`/`ud_s`/`ud_t` parameters, selects the student offer (`offer.isStudent === true`) in `controller:music/subscribe`, and directly invokes `route.send('startListening')` — immediately launching the native Windows Apple Account sign-in and **University Student Plan (1-Month Free Trial, then monthly renewal)** confirmation dialog.

---

## Usage

### Option 1: Double-Click One-Click Run (Recommended)

1. Double-click **`FixAppleMusicStudent.bat`** in the repository root (or run `.\OneClickFix.ps1` in PowerShell).
2. Select your preferred language.
3. The script will automatically configure the temporary WebView2 debug port (`9229`), restart `AppleMusic.exe`, and enable automatic `itmss://` capture.
4. In the opened Apple Music client, go to the subscription plans sheet, select the **University Student** plan, and click **Verify Eligibility** to complete the browser redirect once (or directly paste an existing `ud_s` token / `itmss://` URL).
5. The script automatically binds your student status in the background and brings up the native Apple Music subscription confirmation dialog, then cleans up all temporary environment variables and registry keys.

### Option 2: Command-Line Arguments

```powershell
# Interactive mode in English
.\OneClickFix.ps1 -Lang en

# Direct execution with an existing ud_s token or itmss:// URL
.\OneClickFix.ps1 -Lang en -UdS "<UD_S_TOKEN_OR_ITMSS_URL>"
```

---

## Repository Structure

```text
apple-music-windows-unidays-fix/
├── docs/
│   └── ERRORS_AND_FIXES.md              # Troubleshooting guide for 6 runtime, UIA desktop isolation & CDP errors
├── scripts/
│   ├── bind_unidays_and_checkout.py     # Core binding & checkout trigger engine (supports --lang zh|en)
│   ├── enable_webview2_cdp.ps1          # Standalone WebView2 port 9229 toggle script
│   └── FocusAppleMusic.cs               # WinUI 3 / UWP OpenDesktop("Default") window activation example
├── FixAppleMusicStudent.bat             # Windows double-click launcher (v1.0.0)
├── OneClickFix.ps1                      # Bilingual end-to-end automated fix script (v1.0.0)
├── CHANGELOG.md                         # v1.0.0 release notes (bilingual)
├── README.md                            # English documentation
├── README.zh-CN.md                      # Simplified Chinese documentation
├── .gitignore
└── LICENSE
```

---

## Privacy & Security Statement

Because this script processes client callback parameters at runtime, here is a clear explanation of its privacy and security guarantees:

- **100% Local Execution, Zero Telemetry**: All script operations run strictly on your local machine (connecting only to `127.0.0.1:9229`). There are no third-party network requests, analytics, or backdoors. The request that binds your student status is sent directly from your local Apple Music client to Apple's official servers (`*.itunes.apple.com`).
- **No Credentials Stored**: The intercepted `ud_s` parameter and the client's built-in authentication headers (`X-Dsid`, `X-Token`, etc.) only exist in memory during execution and are discarded immediately afterward. **Nothing is written to local log files**, and console output is sanitized.
- **Automatic Cleanup With Zero Residue**: Both the temporary registry hook (`HKCU\Software\Classes\itmss`) and the WebView2 debugging environment variable are automatically removed and restored inside a `finally` block whether the script finishes normally or exits early.
- **Plain-Text Source Code**: Every file in this repository (`.bat`, `.ps1`, `.py`, `.cs`) is human-readable plain-text source code — no obfuscated or pre-compiled `.exe` binaries are distributed, so you can inspect every line before running.

---

## Disclaimer & Compliance Notice

This project strictly complies with the [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) and applicable laws and regulations:

1. **Not a Crack or Bypass Tool**: This script **cannot bypass** UNiDAYS student eligibility verification. You must already hold a legitimately verified UNiDAYS student account, and you still complete subscription approval through Apple's official native payment dialog. The sole function of this script is to bridge the callback parameter that the Windows client drops.
2. **No Client Binary Modification**: The script only uses Microsoft WebView2's official standard Chrome DevTools Protocol (CDP) interface to trigger frontend routing. **It never modifies, decompiles, or patches any `AppleMusic.exe` binary files**, nor does it involve DLL injection or DRM circumvention.
3. **Strictly Non-Commercial**: This project is free and open-source. Selling, reselling, or using this tool for paid commercial services is strictly prohibited. Once Apple releases an official update fixing the Windows deep-link bug, this repository will be archived.
4. **Trademark Notice**: Apple, Apple Music, iTunes, UNiDAYS, and Windows are registered trademarks of their respective owners. This project is an independent community effort and is not affiliated with, endorsed by, or sponsored by any of the aforementioned companies.

---

## License

Released under the [MIT License](LICENSE). Provided "AS IS" without warranty of any kind; the author assumes no liability for any issues arising from the use or modification of these scripts.
