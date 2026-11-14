# Bug Report for Apple Engineering: Windows Apple Music UWP + UNiDAYS Student Verification Infinite Redirect Loop

---

## Part 1: English Report (For Apple Engineering / Feedback Assistant / Radar)

### Title
**Apple Music for Windows (UWP): Infinite UNiDAYS Student Verification Redirect Loop Due to Dropped `itmss://` Protocol Query Parameters and Unconditional `isStudentOfferSelected` Template Guard in `finance-app`**

### Affected Components
1. **Apple Music for Windows (UWP)**: `AppleInc.AppleMusicWin_nzyj5cx40ttqa` (`AppleMusic.exe`, `WinUIDesktopWin32WindowClass`) — `AppxManifest.xml` `itmss://` protocol activation handler.
2. **AMP Web / `finance-app` (Ember WebView2 bundle)**: `https://finance-app.itunes.apple.com/music/subscribe` (`finance-app/templates/music/subscribe`, `finance-app/controllers/music/subscribe`, `finance-app/routes/music/student-offers`).
3. **AMP Web Redirect**: `https://itunes.apple.com/subscribe?app=music` (returns `HTTP 404 Not Found`).

### Environment
- **OS**: Windows 10 / Windows 11 (x64)
- **Client**: Apple Music for Windows (Microsoft Store UWP package `AppleInc.AppleMusicWin_nzyj5cx40ttqa`)
- **Embedded Runtime**: Microsoft Edge WebView2 (`msedgewebview2.exe`) hosting `https://finance-app.itunes.apple.com`
- **Offer / Plan**: University Student (`salableAdamId: 1608221191`, `offerName: "com.apple.music.AppleMusicStudent"`)

### Steps to Reproduce
1. Sign in to Apple Music for Windows (`AppleMusic.exe`) with an Apple Account whose UNiDAYS student status is already verified (or ready to verify).
2. Click **Try It Free** on the Home tab to open the WebView2 subscription modal (`https://finance-app.itunes.apple.com/music/subscribe?app=music`).
3. Select the **University Student** plan (`salableAdamId: 1608221191`).
4. Notice the primary CTA button changes to **Verify Eligibility** (`action: "verifyEligibility"`), even if the account already has `userInfo.isStudent === true`.
5. Click **Verify Eligibility**. The external browser opens `https://applemusic-spotlight.myunidays.hk/...?urlset=studentSubscriptionOffersiTunes` (or `.com`), completes UNiDAYS verification, and redirects to:
   `itmss://itunes.apple.com/studentSubscriptionOffers?app=music&ud_h=<HASH>&ud_s=<SESSION>&ud_t=<TIMESTAMP>`
6. Windows launches/focuses `AppleMusic.exe` via the `itmss://` protocol handler.

### Actual Results
- `AppleMusic.exe` comes to the foreground, **drops the `/studentSubscriptionOffers` path and `(ud_h, ud_s, ud_t)` query parameters**, and leaves the WebView2 modal on the initial **Verify Eligibility** screen.
- Clicking **Accept Offer / Free Trial** from the UNiDAYS partner web page or Apple Music Web Player (`https://music.apple.com`) navigates to `https://itunes.apple.com/subscribe?app=music`, which returns **`HTTP 404 Not Found`**.

### Expected Results
- `AppleMusic.exe` should forward the `itmss://itunes.apple.com/studentSubscriptionOffers?...` deep link (or its `ud_s` token) to the embedded `finance-app` WebView2 instance, bind the UNiDAYS status via `updateUnidaysStatusSrv` (`POST /commerce/student/updateUnidaysStatus`), and proceed directly to the native **University Student Plan** confirmation sheet (`startListening`).

### Root Cause Analysis (Pinpointed to Exact Modules)

#### 1. `finance-app/templates/music/subscribe` Ignores `isVerifiedStudent`
In the compiled Ember template `finance-app/templates/music/subscribe` (around line 191), the primary CTA button branches exclusively on `isStudentOfferSelected`:
- `["block", "unless", [["get", "isStudentOfferSelected"]]]` -> renders **Try It Free** (`action: "startListening"`).
- `else` -> unconditionally renders **Verify Eligibility** (`action: "verifyEligibility"`).
- **Defect**: It never checks `service:music-subscription`'s `isVerifiedStudent` (`userInfo.isStudent === true`). Consequently, selecting the University Student plan in `music/subscribe` *always* forces the user into `verifyEligibility` -> `verifyWithUnidays("studentSubscriptionOffersiTunes")`.

#### 2. `AppleMusic.exe` UWP `OnActivated` Drops `itmss://` URI & Query Parameters
- `AppleMusic.exe` declares `<uap:Protocol Name="itmss">` in `AppxManifest.xml`.
- However, when Windows dispatches `ProtocolActivatedEventArgs` for `itmss://itunes.apple.com/studentSubscriptionOffers?app=music&ud_h=...&ud_s=...&ud_t=...`, the native host only activates the main `WinUIDesktopWin32WindowClass` window and never routes the embedded WebView2 (`finance-app`) to `/studentSubscriptionOffers` or invokes `updateUnidaysStatusSrv`.

#### 3. Parameter Validation Mismatch on `/studentSubscriptionOffers` vs `updateUnidaysStatusSrv`
- When manually navigating the WebView2 to `/studentSubscriptionOffers?app=music&ud_h=...&ud_s=...&ud_t=...`, downstream checkout via `MZBuy.woa/wa/buyProduct` fails with:
  `"You could not be verified as a university student. Contact UNiDAYS® for support."`
- Conversely, calling `bag.getFromBag('updateUnidaysStatusSrv')` (`POST https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus`) via `Ember.$.ajax` with body `{"ud_s": "<UD_S_TOKEN>"}` returns `HTTP 200` (`{"status": 0}`), and subsequently invoking `route:music/subscribe` -> `send("startListening")` **without** `ud_h`/`ud_s`/`ud_t` query parameters immediately succeeds and triggers the native Windows confirmation & billing sheet.

### Suggested Fix for Apple Engineering
1. **`finance-app/templates/music/subscribe` & `controllers/music/subscribe`**:
   - Update the button condition so that when `isStudentOfferSelected` is `true` **and** `isVerifiedStudent` (`userInfo.isStudent`) is `true`, the template renders the subscribe CTA (`action: "startListening"`) instead of `"Verify Eligibility"` (`action: "verifyEligibility"`).
2. **`AppleMusic.exe` (Windows UWP Native Host)**:
   - In the UWP protocol activation handler (`OnActivated` for `itmss://`), parse incoming `studentSubscriptionOffers` URLs and forward the path and query string (`ud_h`, `ud_s`, `ud_t`) into the active `finance-app` WebView2 session.
3. **Web Redirect (`itunes.apple.com/subscribe`)**:
   - Configure `https://itunes.apple.com/subscribe?app=music` to redirect (`301`/`302`) to `https://music.apple.com/subscribe` instead of returning `HTTP 404`.

---

## Part 2: 中文版问题汇总（供 Apple 中国工程与支持团队参考）

### 问题标题
**Apple Music Windows 版 (UWP)：因客户端丢失 `itmss://` 协议回调参数且 `finance-app` 前端模板忽略 `isVerifiedStudent` 状态，导致 UNiDAYS 大学生验证陷入无限跳转死循环**

### 涉及组件
1. **Apple Music Windows 客户端 (UWP)**：`AppleInc.AppleMusicWin_nzyj5cx40ttqa` (`AppleMusic.exe`) 的 `AppxManifest.xml` `itmss://` 协议激活处理器。
2. **Apple Media Products 前端包 (`finance-app`)**：`https://finance-app.itunes.apple.com/music/subscribe`（`finance-app/templates/music/subscribe`、`finance-app/controllers/music/subscribe`）。
3. **网页端重定向服务**：`https://itunes.apple.com/subscribe?app=music`（当前返回 `HTTP 404 Not Found`）。

### 复现步骤
1. 在 Windows 10/11 打开 `AppleMusic.exe` 并登录已通过（或待通过）UNiDAYS 学生认证的 Apple 账户。
2. 点击“立即试用 (Try It Free)”打开内嵌 WebView2 订阅弹窗（`https://finance-app.itunes.apple.com/music/subscribe?app=music`）。
3. 选中 **大学生 (University Student)** 方案（`salableAdamId: 1608221191`）。
4. 此时无论账户是否已具备学生资格（`userInfo.isStudent === true`），主按钮均强制显示为 **“验证资格 (Verify Eligibility)”**。
5. 点击“验证资格”，外部浏览器跳转至 UNiDAYS 完成认证并回调深链：
   `itmss://itunes.apple.com/studentSubscriptionOffers?app=music&ud_h=<HASH>&ud_s=<SESSION>&ud_t=<TIMESTAMP>`
6. Windows 通过 `itmss://` 协议拉起 `AppleMusic.exe`。

### 实际结果
- `AppleMusic.exe` 仅将主窗口切回前台，**完全丢弃了 `/studentSubscriptionOffers` 路由与 `(ud_h, ud_s, ud_t)` 查询参数**，内嵌 WebView2 仍停留在原“验证资格”界面，形成无限跳转死循环。
- 若从 UNiDAYS 合作页面或 Apple Music 网页播放器（`music.apple.com`）点击“接受优惠/免费试听”，浏览器会跳转到 `https://itunes.apple.com/subscribe?app=music` 并直接返回 **`404 Not Found`**。

### 期望结果
- `AppleMusic.exe` 接管 `itmss://` 激活事件时，应将 `studentSubscriptionOffers` 路由或 `ud_s` 参数透传给内嵌 `finance-app` WebView2，调用 `updateUnidaysStatusSrv` 完成学生身份绑定，并直接拉起 Windows 原生大学生方案订阅确认弹窗。

### 核心根因定位（精确到模块与代码行）

1. **`finance-app/templates/music/subscribe` 模板逻辑缺陷（编译包约第 191 行）**：
   - 模板仅通过 `["block", "unless", [["get", "isStudentOfferSelected"]]]` 分支判断：只要 `isStudentOfferSelected` 为 `true`，就无条件渲染“验证资格”按钮（`action: "verifyEligibility"`），**未检查 `service:music-subscription` 中的 `isVerifiedStudent` (`userInfo.isStudent === true`)**。
2. **Windows UWP `AppleMusic.exe` 未透传 `itmss://` 协议参数**：
   - `AppleMusic.exe` 在 `AppxManifest.xml` 中注册了 `itmss` 协议，但在 `OnActivated` (`ProtocolActivatedEventArgs`) 处理函数中只激活了 `WinUIDesktopWin32WindowClass` 窗口，未把 URI 参数传给 WebView2。
3. **`updateUnidaysStatusSrv` 与 `startListening` 验证实测**：
   - 在 `finance-app` Ember 容器中通过 `Ember.$.ajax` 调用 `bag.getFromBag('updateUnidaysStatusSrv')`（`POST https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus`，请求体 `{"ud_s": "<UD_S_TOKEN>"}`）可直接返回 `HTTP 200`（`{"status": 0}`）。
   - 绑定成功后，在不携带 `ud_h`/`ud_s`/`ud_t` 查询参数的 `/music/subscribe` 路由下调用 `route:music/subscribe` 的 `send("startListening")`，即可正常弹出 Windows 原生大学生方案确认框与银联/支付验证窗口并完成订阅。

### 给 Apple 工程团队的修复建议
1. **修复 `finance-app/templates/music/subscribe`**：当 `isStudentOfferSelected && isVerifiedStudent` 同时为 `true` 时，直接渲染订阅按钮（触发 `startListening`），而非“验证资格（`verifyEligibility`）”。
2. **修复 `AppleMusic.exe` UWP 协议处理**：在 `itmss://` 协议唤醒时，将 `studentSubscriptionOffers` 及其查询参数（或 `ud_s`）转发至内嵌 WebView2 执行 `updateUnidaysStatusSrv` 绑定与结账流程。
3. **修复网页端兜底重定向**：将失效的 `https://itunes.apple.com/subscribe?app=music` 重定向至有效的 `https://music.apple.com/subscribe`。
