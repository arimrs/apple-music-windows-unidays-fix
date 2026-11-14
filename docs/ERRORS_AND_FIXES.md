# Errors & Fixes Catalog

A structured reference of every error and edge case encountered while diagnosing and automating **Apple Music (Windows UWP)** + **UNiDAYS** student verification.

---

## 1. Infinite UNiDAYS Verification Redirect Loop

- **Symptom**: Clicking **Verify Eligibility** on the University Student plan opens the browser to UNiDAYS, redirects back to `AppleMusic.exe`, and lands on the exact same **Verify Eligibility** button repeatedly.
- **Root Cause**:
  1. `finance-app/templates/music/subscribe` renders `"Verify Eligibility"` (`action: "verifyEligibility"`) whenever the student offer (`1608221191`) is selected, ignoring `service:music-subscription`'s `isVerifiedStudent` flag.
  2. Windows `AppleMusic.exe` (`AppxManifest.xml`) intercepts `itmss://itunes.apple.com/studentSubscriptionOffers?...` without forwarding the route or `(ud_h, ud_s, ud_t)` query parameters to `finance-app`.
- **Fix**:
  - Extract `ud_s` from the UNiDAYS redirect URL.
  - Call `POST https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus` with `{"ud_s": "<UD_S_TOKEN>"}` inside `finance-app` (`HTTP 200`, `{"status": 0}`).
  - Trigger `startListening` for `salableAdamId=1608221191` / `offerName=com.apple.music.AppleMusicStudent` directly.

---

## 2. `404 Not Found` on `https://itunes.apple.com/subscribe?app=music`

- **Symptom**: Clicking the offer CTA on the UNiDAYS partner page or Apple Music Web Player opens `https://itunes.apple.com/subscribe?app=music`, which fails with `404 Not Found`.
- **Root Cause**: Legacy `itunes.apple.com/subscribe` web endpoint is deprecated/unrouted for desktop browsers without an active native protocol handoff.
- **Fix**: Do not rely on the web redirect URL; perform UNiDAYS token binding (`updateUnidaysStatus`) and checkout inside the native `AppleMusic.exe` WebView2 `finance-app` context.

---

## 3. `MZBuy.woa/wa/buyProduct` Student Verification Error on Replay

- **Symptom**: Navigating WebView2 manually to `studentSubscriptionOffers` with `(ud_h, ud_s, ud_t)` fails at checkout with:
  > *"You could not be verified as a university student. Contact UNiDAYS® for support."*
- **Root Cause**: Passing `ud_h` / `ud_s` / `ud_t` via a manually constructed `studentSubscriptionOffers` route triggers strict referral/token validation in `MZBuy.woa/wa/buyProduct` that fails outside the native iTunes handshake.
- **Fix**: Bind `ud_s` first via `POST /commerce/student/updateUnidaysStatus`, then start the checkout on `route:music/subscribe` **without** `ud_h`/`ud_s`/`ud_t` query parameters.

---

## 4. Background PowerShell / UIAutomation Cannot Find UWP Windows

- **Symptom**:
  - `(Get-Process AppleMusic).MainWindowHandle` returns `0`.
  - `AutomationElement.RootElement.FindFirst(TreeScope.Children, ...)` returns `$null` (`"No Apple Music AutomationElement found"`) when run from a non-interactive/background PowerShell session.
- **Root Cause**:
  1. WinUI 3 / UWP apps (`WinUIDesktopWin32WindowClass`) often expose `0` as `MainWindowHandle` on `System.Diagnostics.Process`.
  2. Background console processes may not be attached to the interactive `"Default"` desktop station, causing `RootElement` enumeration and `EnumWindows` to return empty results.
- **Fix**:
  - Explicitly attach the thread to the interactive desktop before calling UIAutomation or `EnumWindows`:
    ```csharp
    IntPtr hd = OpenDesktop("Default", 0, false, 0x01FF);
    if (hd != IntPtr.Zero) SetThreadDesktop(hd);
    ```
  - Enumerate top-level `AutomationElement.RootElement.FindAll(TreeScope.Children, Condition.TrueCondition)` and match by `ProcessName` / `ClassName` (`WinUIDesktopWin32WindowClass`).

---

## 5. Global UIAutomation Clicker Hitting Background Windows

- **Symptom**: A generic UIAutomation button clicker searching `RootElement` for `"Settings"` clicked a completely different application's **Settings** button behind `Apple Music` because `SetForegroundWindow` was blocked by Windows foreground lock.
- **Root Cause**:
  1. `SetForegroundWindow` from a background process is silently ignored by Windows when another app holds the foreground lock.
  2. Searching `AutomationElement.RootElement` top-down matches the first visible window containing that button name.
- **Fix**:
  - Scope UIAutomation searches strictly to the target window's `AutomationElement` (`winEl.FindFirst(...)`), never `RootElement`.
  - Verify the target window is actually brought to front (`ShowWindow` + `SetWindowPos(HWND_TOPMOST)` -> `SetForegroundWindow` -> `SetWindowPos(HWND_NOTOPMOST)`) before dispatching synthetic mouse events.

---

## 6. WebView2 CDP Port `127.0.0.1:9229` Refusing Connections After Billing Sheet Closes

- **Symptom**: `http://127.0.0.1:9229/json` throws `ConnectionRefusedError: [WinError 10061]` right after completing payment verification.
- **Root Cause**: `AppleMusic.exe` only spawns `msedgewebview2.exe` while a WebView2 modal/account/checkout sheet is open. Once payment verification finishes, the sheet closes and `msedgewebview2.exe` exits cleanly.
- **Fix**:
  - Re-open **View My Account** (or another account/subscription sheet) inside `AppleMusic.exe` if you need to re-attach CDP.
  - Always clean up `HKCU\Environment\WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` once debugging is complete so WebView2 does not leave a debug port open permanently.
