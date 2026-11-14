# Apple Music Windows 端 + UNiDAYS 学生验证无限跳转一键修复工具

**🇨🇳 简体中文 | [🇺🇸 English](README.md)**

[![Release](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows)](https://www.microsoft.com/windows)
[![App](https://img.shields.io/badge/Client-Apple%20Music%20UWP-FA243C?logo=applemusic)](https://apps.microsoft.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 本工具用于临时解决 **Windows 版 Apple Music (`AppleMusic.exe`) 已通过 UNiDAYS 学生验证，但客户端依然反复跳转、无法完成学生订阅** 的 Bug。目前该问题已反馈给 Apple 等待官方修复。本项目完全开源免费，仅作技术排错与学习交流，**不具备绕过学生验证或破解付费的功能**，也不涉及任何商业用途。

---

请注意，经排查该问题并非偶发的网络波动或账号异常，而是由 **Apple 服务端 `finance-app` 前端代码逻辑缺陷** 与 **Windows UWP 客户端 `AppxManifest.xml` 协议处理缺失** 共同导致的必然现象，因其在所有 Windows 10/11 客户端上均可稳定复现：

1. **前端模板无视已验证状态（`finance-app/templates/music/subscribe` 第 191 行）**：
   - 模板通过 `["block", "unless", [["get", "isStudentOfferSelected"]]]` 控制主按钮：只要用户选中了**大学生方案**（`salableAdamId: 1608221191`），按钮就无条件变成 **“验证资格 (Verify Eligibility)”**（`action: "verifyEligibility"`），完全忽略了 `service:music-subscription` 中已存在的 `isVerifiedStudent`（`userInfo.isStudent === true`）状态。
2. **Windows UWP 客户端丢失 `itmss://` 深链回调参数**：
   - 点击“验证资格”会调用 `verifyWithUnidays("studentSubscriptionOffersiTunes")`，拉起浏览器跳转至 UNiDAYS 并返回：
     `itmss://itunes.apple.com/studentSubscriptionOffers?app=music&ud_h=...&ud_s=...&ud_t=...`
   - Windows 版 `AppleMusic.exe` 在 `AppxManifest.xml` 中注册了 `itmss://` 协议，但被唤醒时**仅激活主窗口，未将 `studentSubscriptionOffers` 路由及 `(ud_h, ud_s, ud_t)` 参数透传给内嵌的 WebView2 (`finance-app`)**，导致死循环回到原界面。
3. **手动回放深链参数被后端拒绝 + 网页端兜底链接 `404`**：
   - 若强行让 WebView2 跳转到带 `(ud_h, ud_s, ud_t)` 的 `studentSubscriptionOffers`，`MZBuy.woa/wa/buyProduct` 会报错 `"You could not be verified as a university student. Contact UNiDAYS® for support."`。
   - 从 UNiDAYS 网页端或 Apple Music 网页播放器点击“接受优惠/免费试听”则会跳转到 `https://itunes.apple.com/subscribe?app=music`，直接返回 **`404 Not Found`**。

### 如何解决？

1. **自动拦截提取 `ud_s`**：通过临时注册 `HKCU\Software\Classes\itmss` 协议钩子，当浏览器完成 UNiDAYS 验证并回跳 `itmss://` 时，脚本自动捕获其中的 `ud_s` Token（捕获后立即清理该注册表项，无需手动抓包）。
2. **通过 Ember 内部容器与 `Ember.$.ajax` 绑定学生身份**：
   - 连接 `AppleMusic.exe` 内嵌 WebView2 的 CDP 端口（`127.0.0.1:9229`），获取真实的 Ember 容器 `Ember.Namespace.NAMESPACES.find(n => n && n.__container__)`。
   - 从 `service:itunes-bag` 读取 `updateUnidaysStatusSrv`（即 `https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus`），并通过 **`Ember.$.ajax`** 发送 `POST {"ud_s": "<TOKEN>"}`（自动触发 `Ember.$.ajaxPrefilter` 注入当前客户端的 `X-Apple-Store-Front`、`X-Dsid` 与 `X-Token` 认证头），返回 `HTTP 200` 及 `{"status": 0}`。
3. **在纯净 `/music/subscribe` 路由直接拉起原生结账**：
   - 剔除会导致风控报错的 `ud_h`/`ud_s`/`ud_t` 参数，在 `controller:music/subscribe` 中选中 `offer.isStudent === true` 的大学生方案，直接调用 `route.send('startListening')`，立即弹出 Windows 原生 Apple 账户登录与 **大学生方案（前 1 个月免费，之后 ¥7.00/月）** 确认弹窗。

---

## 使用方法

### 方式一：双击一键运行（Recommended）

1. 双击运行仓库根目录下的 **`FixAppleMusicStudent.bat`**（或在 PowerShell 中运行 `.\OneClickFix.ps1`）。
2. 选择语言。
3. 脚本会自动配置临时 WebView2 调试端口（`9229`）、重启 `AppleMusic.exe`，并开启 `itmss://` 自动捕获。
4. 在打开的 Apple Music 客户端中进入订阅方案页，选中 **大学生** 方案并点击 **验证资格 (Verify Eligibility)** 完成一次浏览器跳转（或直接粘贴已有的 `ud_s` Token / `itmss://` 链接）。
5. 脚本自动完成后台学生状态绑定并弹出 Apple Music 原生订阅确认框，随后自动清理所有临时环境变量与注册表项。

### 方式二：命令行参数运行

```powershell
# 中文交互模式
.\OneClickFix.ps1 -Lang zh

# 已持有 ud_s Token 或 itmss:// 链接时直接一键执行
.\OneClickFix.ps1 -Lang zh -UdS "<UD_S_TOKEN_OR_ITMSS_URL>"
```

---

## 仓库目录结构

```text
apple-music-windows-unidays-fix/
├── docs/
│   └── ERRORS_AND_FIXES.md              # 6 类核心运行错误、UIA 桌面隔离与 CDP 排错手册
├── scripts/
│   ├── bind_unidays_and_checkout.py     # 核心绑定与触发结账引擎（支持中英双语 --lang zh|en）
│   ├── enable_webview2_cdp.ps1          # 独立 WebView2 9229 调试端口开关脚本
│   └── FocusAppleMusic.cs               # WinUI 3 / UWP OpenDesktop("Default") 窗口激活示例
├── FixAppleMusicStudent.bat             # Windows 双击一键启动器 (v1.0.0)
├── OneClickFix.ps1                      # 中英双语全流程一键修复主脚本 (v1.0.0)
├── CHANGELOG.md                         # v1.0.0 版本发布说明（中英双语）
├── README.md                            # 英文版说明文档
├── README.zh-CN.md                      # 简体中文版说明文档
├── .gitignore
└── LICENSE
```

---

## 隐私与安全说明

由于脚本运行过程中需要处理客户端回调参数，这里对隐私安全做个明确说明：

- **纯本地运行，零联网上报**：脚本所有操作均在本地完成（仅连接本机 `127.0.0.1:9229` 调试端口），没有任何第三方网络请求、统计代码或后门。向 Apple 提交学生状态的请求，是由你本机的 Apple Music 客户端直接发往 Apple 官方服务器（`*.itunes.apple.com`）的。
- **不保存任何账号凭证**：拦截到的 `ud_s` 参数以及客户端内置的 `X-Dsid`、`X-Token` 等认证头仅在脚本运行时的内存里走一遍，用完即焚，**不会写入任何本地日志文件**，控制台输出也做了脱敏处理。
- **用完自动清理，不留残余**：脚本为了拦截回调而临时写入的注册表项（`HKCU\Software\Classes\itmss`）和调试端口环境变量，在运行结束或中途关闭时都会自动清理还原，不会污染系统环境。
- **全明文源码**：仓库里所有代码（`.bat`、`.ps1`、`.py`、`.cs`）均为明文脚本，没有打包成不明 `.exe` 可执行文件，随时可以打开源码直接检查。

---

## 免责与合规声明

本项目严格遵守 [GitHub 服务条款](https://docs.github.com/zh/site-policy/github-terms/github-terms-of-service) 及相关法律法规：

1. **非破解、非白嫖工具**：本脚本**不能绕过** UNiDAYS 的学生资格审核。使用前提是你本人已经合法通过了 UNiDAYS 验证，且最后依然需要通过 Apple 官方弹出的原生付款窗口完成订阅。脚本干的唯一一件事，就是帮 Windows 客户端把弄丢的跳转参数重新接上。
2. **不篡改客户端文件**：脚本仅调用微软 WebView2 官方提供的标准 CDP 调试接口执行前端路由跳转，**不会修改、反编译或修补 `AppleMusic.exe` 的任何二进制文件**，也不涉及 DLL 注入或任何 DRM 音频加密绕过。
3. **禁止商业倒卖**：本项目完全免费开源，严禁任何个人或店铺将其用于淘宝/闲鱼代充、付费代修等商业牟利行为。一旦 Apple 官方更新修复了 Windows 端的跳转 Bug，本仓库将直接归档（Archive）。
4. **商标声明**：文中提到的 Apple、Apple Music、iTunes、UNiDAYS、Windows 等名称均为其各自所属公司的注册商标，本项目为独立个人开发，与上述公司没有任何关联。

---

## 开源许可

本项目基于 [MIT License](LICENSE) 开源，按“原样（AS IS）”提供，开发者不对使用或修改本脚本可能产生的任何问题承担责任。
