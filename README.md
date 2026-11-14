# Apple Music Windows + UNiDAYS Student Verification One-Click Fix (`v1.0.0`)

**[🇨🇳 简体中文](README.zh-CN.md) | 🇺🇸 English**

[![Release](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows)](https://www.microsoft.com/windows)
[![App](https://img.shields.io/badge/Client-Apple%20Music%20UWP-FA243C?logo=applemusic)](https://apps.microsoft.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **One-Click Fix (`v1.0.0`)** and root-cause analysis for the **Apple Music on Windows + UNiDAYS student verification infinite redirect loop**, supporting both **Chinese (`zh`)** and **English (`en`)**.

---

## Why Is This Bug 100% Reproducible? (Root Cause Analysis)

Both the symptom and the fix are **100% deterministic and reproducible** on Windows because the bug stems from static client/template logic in Apple's `finance-app` Ember bundle (`https://finance-app.itunes.apple.com`) and the Windows UWP `AppxManifest.xml` protocol registration of `AppleMusic.exe`:

1. **Unconditional "Verify Eligibility" Button in `finance-app/templates/music/subscribe`**:
   - Line 191 of `templates/music/subscribe` checks `["block", "unless", [["get", "isStudentOfferSelected"]]]` to toggle between **Try It Free** (`action: "startListening"`) and **Verify Eligibility** (`action: "verifyEligibility"`).
   - It **completely ignores** `service:music-subscription`'s `isVerifiedStudent` property (`userInfo.isStudent === true`). Thus, selecting **University Student** (`salableAdamId: 1608221191`) on Windows *always* renders **Verify Eligibility**.
2. **`itmss://` Deep-Link Parameter Loss in Windows UWP (`AppleMusic.exe`)**:
   - Clicking **Verify Eligibility** invokes `verifyWithUnidays("studentSubscriptionOffersiTunes")`, opening the browser to UNiDAYS (`applemusic-spotlight.myunidays.hk` / `.com`), which redirects to:
     `itmss://itunes.apple.com/studentSubscriptionOffers?app=music&ud_h=...&ud_s=...&ud_t=...`
   - Windows UWP `AppleMusic.exe` handles the `itmss://` protocol activation in `AppxManifest.xml` solely by focusing the main window **without passing the `studentSubscriptionOffers` route or `(ud_h, ud_s, ud_t)` query parameters** into the embedded WebView2 (`finance-app`).
3. **Backend Rejection on Manual Deep-Link Replay & `404` on Web Fallback**:
   - Manually navigating WebView2 to `studentSubscriptionOffers` with `(ud_h, ud_s, ud_t)` causes `MZBuy.woa/wa/buyProduct` to fail with `"You could not be verified as a university student. Contact UNiDAYS® for support."`
   - Clicking the offer button on the UNiDAYS partner web page or Apple Music Web Player opens `https://itunes.apple.com/subscribe?app=music`, which returns **`404 Not Found`**.

### Why the `v1.0.0` Fix Works Deterministically

Instead of relying on the broken `itmss://` deep-link handoff:
1. We intercept `ud_s` automatically from the `itmss://` redirect via a temporary `HKCU\Software\Classes\itmss` hook (cleaned up immediately after capture).
2. Inside the live `finance-app.itunes.apple.com` Ember container (`Ember.Namespace.NAMESPACES.find(n => n && n.__container__)`), we resolve `bag.getFromBag('updateUnidaysStatusSrv')` (`https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus`) and invoke `Ember.$.ajax({ method: 'POST', data: JSON.stringify({ ud_s }) })` — which runs `Ember.$.ajaxPrefilter` to attach the native `X-Apple-Store-Front`, `X-Dsid`, and `X-Token` headers automatically, returning `HTTP 200` (`{"status": 0}`).
3. Finally, on a clean `/music/subscribe` route (without `ud_h`/`ud_s`/`ud_t`), we select the Student offer (`offer.isStudent === true`) on `controller:music/subscribe` and invoke `route.send('startListening')`, immediately popping the native Windows Apple Music **Student (1-Month Free Trial, then renewal)** confirmation sheet.

---

## One-Click Fix (`v1.0.0`) Usage

### Option A: Double-Click One-Click Launcher (Recommended)

1. Double-click **`FixAppleMusicStudent.bat`** (or run `.\OneClickFix.ps1` in PowerShell).
2. Select your language (`[1] 中文 (简体)` or `[2] English`).
3. The script will automatically:
   - Enable WebView2 CDP on `127.0.0.1:9229` and restart `AppleMusic.exe`.
   - Set a temporary `itmss://` capture hook.
4. In `AppleMusic.exe`, open the subscription plans sheet, select **University Student**, click **Verify Eligibility** (and finish UNiDAYS in your browser), **or** paste an existing `itmss://...&ud_s=...` URL/token.
5. The script automatically binds `ud_s` via `updateUnidaysStatusSrv`, triggers the native Student checkout dialog, and cleans up all temporary registry keys (`WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` and `itmss` hook).

### Option B: Command-Line Usage

```powershell
# Interactive (Chinese or English)
.\OneClickFix.ps1 -Lang en

# Direct with an already-captured ud_s token or itmss:// URL
.\OneClickFix.ps1 -Lang en -UdS "<UD_S_TOKEN_OR_ITMSS_URL>"
```

---

## Repository Structure

```text
apple-music-windows-unidays-fix/
├── docs/
│   └── ERRORS_AND_FIXES.md              # Detailed catalog of 6 runtime/UIA/CDP errors & fixes
├── scripts/
│   ├── bind_unidays_and_checkout.py     # Core Ember.$.ajax updateUnidaysStatusSrv + startListening engine
│   ├── enable_webview2_cdp.ps1          # Standalone WebView2 port 9229 toggle utility
│   └── FocusAppleMusic.cs               # WinUI 3 / UWP OpenDesktop("Default") UIAutomation helper
├── FixAppleMusicStudent.bat             # One-click double-click launcher (v1.0.0)
├── OneClickFix.ps1                      # Bilingual (ZH/EN) end-to-end automated fix script (v1.0.0)
├── CHANGELOG.md                         # Release notes for v1.0.0
├── README.md                            # English documentation
├── README.zh-CN.md                      # Chinese documentation (简体中文文档)
├── .gitignore
└── LICENSE
```

---

## Privacy & Sanitization Notice

This repository contains **zero** personal credentials, Apple IDs, passwords, DSIDs, phone numbers, or session tokens (`ud_s`, `ud_t`, `ud_h`). All user-specific values are dynamically captured at runtime on the user's own machine.

---

## License

Released under the [MIT License](LICENSE).
