# Apple Music Windows 端 + UNiDAYS 学生验证无限跳转一键修复工具 (`v1.0.0`)

**🇨🇳 简体中文 | [🇺🇸 English](README.md)**

[![Release](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows)](https://www.microsoft.com/windows)
[![App](https://img.shields.io/badge/Client-Apple%20Music%20UWP-FA243C?logo=applemusic)](https://apps.microsoft.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 针对 **Windows 版 Apple Music (`AppleMusic.exe`) 已通过 UNiDAYS 学生验证却反复跳转、无法完成学生订阅** 问题的根因剖析与 **`v1.0.0` 中英双语一键修复工具**。

---

## 为什么该问题与修复方案 100% 可复现？（核心原理剖析）

该问题并非偶发的网络波动或账号异常，而是由 **Apple 服务端 `finance-app` 前端代码逻辑缺陷** 与 **Windows UWP 客户端 `AppxManifest.xml` 协议处理缺失** 共同导致的**必然现象**，因此在所有 Windows 10/11 客户端上 **100% 稳定复现**：

1. **前端模板无视已验证状态（`finance-app/templates/music/subscribe` 第 191 行）**：
   - 模板通过 `["block", "unless", [["get", "isStudentOfferSelected"]]]` 控制主按钮：只要用户选中了**大学生方案**（`salableAdamId: 1608221191`），按钮就无条件变成 **“验证资格 (Verify Eligibility)”**（`action: "verifyEligibility"`），完全忽略了 `service:music-subscription` 中已存在的 `isVerifiedStudent`（`userInfo.isStudent === true`）状态。
2. **Windows UWP 客户端丢失 `itmss://` 深链回调参数**：
   - 点击“验证资格”会调用 `verifyWithUnidays("studentSubscriptionOffersiTunes")`，拉起浏览器跳转至 UNiDAYS 并返回：
     `itmss://itunes.apple.com/studentSubscriptionOffers?app=music&ud_h=...&ud_s=...&ud_t=...`
   - Windows 版 `AppleMusic.exe` 在 `AppxManifest.xml` 中注册了 `itmss://` 协议，但被唤醒时**仅激活主窗口，未将 `studentSubscriptionOffers` 路由及 `(ud_h, ud_s, ud_t)` 参数透传给内嵌的 WebView2 (`finance-app`)**，导致死循环回到原界面。
3. **手动回放深链参数被后端拒绝 + 网页端兜底链接 `404`**：
   - 若强行让 WebView2 跳转到带 `(ud_h, ud_s, ud_t)` 的 `studentSubscriptionOffers`，`MZBuy.woa/wa/buyProduct` 会报错 `"You could not be verified as a university student. Contact UNiDAYS® for support."`。
   - 从 UNiDAYS 网页端或 Apple Music 网页播放器点击“接受优惠/免费试听”则会跳转到 `https://itunes.apple.com/subscribe?app=music`，直接返回 **`404 Not Found`**。

### `v1.0.0` 一键修复脚本为什么能 100% 稳定解决？

1. **自动拦截提取 `ud_s`**：通过临时注册 `HKCU\Software\Classes\itmss` 协议钩子，当浏览器完成 UNiDAYS 验证并回跳 `itmss://` 时，脚本自动捕获其中的 `ud_s` Token（捕获后立即清理该注册表项，无需手动抓包）。
2. **通过 Ember 内部容器与 `Ember.$.ajax` 绑定学生身份**：
   - 连接 `AppleMusic.exe` 内嵌 WebView2 的 CDP 端口（`127.0.0.1:9229`），获取真实的 Ember 容器 `Ember.Namespace.NAMESPACES.find(n => n && n.__container__)`。
   - 从 `service:itunes-bag` 读取 `updateUnidaysStatusSrv`（即 `https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus`），并通过 **`Ember.$.ajax`** 发送 `POST {"ud_s": "<TOKEN>"}`（自动触发 `Ember.$.ajaxPrefilter` 注入当前客户端的 `X-Apple-Store-Front`、`X-Dsid` 与 `X-Token` 认证头），返回 `HTTP 200` 及 `{"status": 0}`。
3. **在纯净 `/music/subscribe` 路由直接拉起原生结账**：
   - 剔除会导致风控报错的 `ud_h`/`ud_s`/`ud_t` 参数，在 `controller:music/subscribe` 中选中 `offer.isStudent === true` 的大学生方案，直接调用 `route.send('startListening')`，立即弹出 Windows 原生 Apple 账户登录与 **大学生方案（前 1 个月免费，之后 ¥7.00/月）** 确认弹窗。

---

## 一键修复工具 (`v1.0.0`) 使用方法

### 方式一：双击一键运行（推荐）

1. 双击运行仓库根目录下的 **`FixAppleMusicStudent.bat`**（或在 PowerShell 中运行 `.\OneClickFix.ps1`）。
2. 输入 `1` 选择 **中文 (简体)**，或输入 `2` 选择 **English**。
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

## 隐私与脱敏声明

本仓库已完成全量脱敏，**不包含**任何个人 Apple 账号、密码、DSID、手机号或 `ud_s`/`ud_t`/`ud_h` 凭据。所有验证参数均在用户本地运行时动态捕获并仅用于向 Apple 官方接口发起绑定请求。

---

## 开源许可

本项目基于 [MIT License](LICENSE) 开源。
