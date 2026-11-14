# Changelog / 版本更新日志

## [v1.0.0] - 2026-11-14

### English
- **Added**: `FixAppleMusicStudent.bat` & `OneClickFix.ps1` one-click automated fix script with interactive and CLI bilingual support (`zh` / `en`).
- **Added**: Automatic `itmss://` redirect capture hook in `OneClickFix.ps1` so users do not need to manually extract `ud_s` from browser DevTools.
- **Added**: `scripts/bind_unidays_and_checkout.py` (`v1.0.0`) using the live Ember container (`Ember.Namespace.NAMESPACES`), `service:itunes-bag` (`updateUnidaysStatusSrv`), `Ember.$.ajax` (preserving native `X-Apple-Store-Front` & `X-Token` headers), and `route:music/subscribe` `startListening`.
- **Added**: Bilingual documentation (`README.md` in English, `README.zh-CN.md` in Simplified Chinese) and `docs/ERRORS_AND_FIXES.md`.
- **Security**: Strictly sanitized all code and documentation; zero hardcoded accounts, passwords, DSIDs, or tokens.

### 简体中文
- **新增**：`FixAppleMusicStudent.bat` 与 `OneClickFix.ps1` 一键修复工具，支持中英双语交互与命令行调用（`-Lang zh|en`）。
- **新增**：自动拦截捕获 `itmss://` 浏览器回跳链接中的 `ud_s` Token，无需手动打开浏览器开发者工具抓包，并在 `finally` 中自动还原清理注册表。
- **新增**：`scripts/bind_unidays_and_checkout.py` (`v1.0.0`)，基于真实 Ember 容器（`Ember.Namespace.NAMESPACES`）、`service:itunes-bag`（`updateUnidaysStatusSrv`）与 `Ember.$.ajax`（自动携带 `X-Apple-Store-Front` 与 `X-Token` 请求头）完成学生身份绑定，并在纯净 `/music/subscribe` 路由触发 `startListening` 原生结账。
- **新增**：中英双语文档（`README.zh-CN.md`、`README.md`）与 6 类错误排查手册（`docs/ERRORS_AND_FIXES.md`）。
- **安全脱敏**：全仓库与脚本 100% 去敏，不含任何个人账号、密码、DSID 或 Token。
