# Apple Music Windows + UNiDAYS Student Verification Fix & Postmortem

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows)](https://www.microsoft.com/windows)
[![App](https://img.shields.io/badge/Client-Apple%20Music%20UWP-FA243C?logo=applemusic)](https://apps.microsoft.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> A technical root-cause analysis and reference guide for fixing the **Apple Music on Windows + UNiDAYS student verification infinite redirect loop**, along with a structured catalog of Windows UIAutomation / WebView2 debugging errors encountered during automation.

---

## Table of Contents

- [Problem Overview](#problem-overview)
- [Root Cause Analysis](#root-cause-analysis)
- [Working Resolution](#working-resolution)
- [Errors & Fixes Catalog](#errors--fixes-catalog)
- [Repository Structure](#repository-structure)
- [Security & Privacy Note](#security--privacy-note)
- [License](#license)

---

## Problem Overview

On Windows (`AppleMusic.exe` UWP + WebView2 `finance-app`), users who already hold a valid **UNiDAYS** student verification frequently encounter an endless redirect loop:

1. Selecting the **University Student** plan inside Apple Music displays **Verify Eligibility** even after UNiDAYS verification succeeded.
2. Clicking **Verify Eligibility** opens the browser to UNiDAYS, which redirects back via `itmss://itunes.apple.com/studentSubscriptionOffers?...`.
3. Windows launches/focuses `AppleMusic.exe`, which **ignores the deep-link query parameters** and returns to the same **Verify Eligibility** screen.
4. Clicking **Accept Offer / Free Trial** from the UNiDAYS partner page or Apple Music Web Player opens `https://itunes.apple.com/subscribe?app=music`, which returns **`404 Not Found`**.

---

## Root Cause Analysis

Inspection of Apple Music's embedded WebView2 `finance-app` bundle revealed four compounding issues:

| Component | Behavior / Defect | Impact |
| :--- | :--- | :--- |
| `finance-app/templates/music/subscribe` | Uses `isStudentOfferSelected` to unconditionally render **Verify Eligibility** (`action: "verifyEligibility"`), ignoring `service:music-subscription`'s `isVerifiedStudent` (`userInfo.isStudent === true`). | Client UI keeps asking to verify even when the account is already eligible. |
| `verifyWithUnidays("studentSubscriptionOffersiTunes")` | Opens `applemusic-spotlight.myunidays.hk/...` in an external browser, returning `itmss://itunes.apple.com/studentSubscriptionOffers?app=music&ud_h=...&ud_s=...&ud_t=...`. | Hand-off relies on `itmss://` protocol parsing. |
| `AppleMusic.exe` (`AppxManifest.xml`) | Handles `itmss://` activation without forwarding the `studentSubscriptionOffers` route or `(ud_h, ud_s, ud_t)` parameters into the WebView2 `finance-app` instance. | Deep link drops all verification tokens and loops back to the start. |
| `MZBuy.woa/wa/buyProduct` + Web redirect | Navigating WebView2 manually to `studentSubscriptionOffers` with `(ud_h, ud_s, ud_t)` fails validation; external web links to `itunes.apple.com/subscribe?app=music` return `404 Not Found`. | Neither manual deep-link replay nor web fallback completes checkout. |

---

## Working Resolution

Instead of relying on the broken `itmss://` deep-link handoff, bind the UNiDAYS token directly inside the authenticated `finance-app` WebView2 context and trigger the student offer checkout directly:

1. **Extract `ud_s` from UNiDAYS**
   - Complete UNiDAYS login in the browser and capture the redirect URL (`itmss://itunes.apple.com/studentSubscriptionOffers?...&ud_s=<UD_S_TOKEN>&...`).
2. **Bind UNiDAYS Status via `updateUnidaysStatus`**
   - Inside the WebView2 `finance-app` origin (`https://finance-app.itunes.apple.com`), send:
     ```http
     POST https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus
     Content-Type: application/json

     { "ud_s": "<UD_S_TOKEN>" }
     ```
   - Expected response: `HTTP 200` with `{"status": 0}`.
3. **Trigger Student Plan Checkout Without Deep-Link Params**
   - Invoke `route:music/subscribe` `send('startListening')` with the University Student offer (`salableAdamId: 1608221191`, `offerName: "com.apple.music.AppleMusicStudent"`) without `ud_h` / `ud_s` / `ud_t`.
   - Complete the native **Sign-In Required** prompt, click **Confirm** on the Student Trial sheet, and complete **Billing Info** verification (e.g., UnionPay SMS OTP).
4. **Verify Active Subscription**
   - Confirm the home screen switches from the trial upsell banner to the subscriber home view and that full-length tracks play past the 30-second preview limit.

---

## Errors & Fixes Catalog

All runtime errors, Windows UIAutomation pitfalls, and WebView2 CDP issues encountered during diagnosis and automation are documented in detail in:

- 📄 [**`docs/ERRORS_AND_FIXES.md`**](docs/ERRORS_AND_FIXES.md)

---

## Repository Structure

```text
apple-music-windows-unidays-fix/
├── docs/
│   └── ERRORS_AND_FIXES.md              # Detailed error catalog, symptoms, root causes, and fixes
├── scripts/
│   ├── enable_webview2_cdp.ps1          # Toggle WebView2 remote debugging port 9229 cleanly
│   ├── bind_unidays_and_checkout.py     # Bind ud_s via updateUnidaysStatus & trigger student checkout
│   └── FocusAppleMusic.cs               # Desktop-aware UIAutomation helper for WinUI 3 / UWP
├── .gitignore
├── LICENSE
└── README.md
```

### Quick Reproduction Steps

1. Enable WebView2 CDP on port `9229`:
   ```powershell
   .\scripts\enable_webview2_cdp.ps1 -Enable
   ```
2. Restart `AppleMusic.exe` and open the subscription/account sheet so `finance-app.itunes.apple.com` loads.
3. Obtain your `ud_s` token from the UNiDAYS redirect (`itmss://itunes.apple.com/studentSubscriptionOffers?...&ud_s=<UD_S_TOKEN>&...`).
4. Bind `ud_s` and trigger checkout:
   ```bash
   pip install websocket-client
   python .\scripts\bind_unidays_and_checkout.py --ud-s "<UD_S_TOKEN>" --checkout
   ```
5. Complete Apple Account sign-in, click **Confirm**, finish billing verification, and disable WebView2 CDP when done:
   ```powershell
   .\scripts\enable_webview2_cdp.ps1 -Disable
   ```

---

## Security & Privacy Note

All account identifiers, passwords, DSIDs, phone numbers, and UNiDAYS/Apple session tokens (`ud_s`, `ud_t`, `ud_h`) have been stripped and replaced with placeholders such as `<UD_S_TOKEN>` and `<APPLE_ACCOUNT>`.

---

## License

Released under the [MIT License](LICENSE).
