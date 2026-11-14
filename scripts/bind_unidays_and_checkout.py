#!/usr/bin/env python3
"""
Apple Music (Windows UWP) + UNiDAYS Student Verification Fix (v1.0.0)
Binds a verified UNiDAYS `ud_s` token directly inside Apple Music's embedded
`finance-app` WebView2 using Ember's `service:itunes-bag` (`updateUnidaysStatusSrv`)
and `Ember.$.ajax` (preserving Apple Storefront / X-Token headers), then triggers
`route:music/subscribe` `startListening` for the University Student offer without
broken `itmss://` (`ud_h`/`ud_s`/`ud_t`) deep-link parameters.
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import websocket  # pip install websocket-client

VERSION = "1.0.0"

I18N = {
    "zh": {
        "wait_wv": "正在等待 Apple Music 打开订阅页面 (finance-app.itunes.apple.com, 端口 {port})...",
        "open_hint": "提示：如果尚未打开订阅页，请在 Apple Music 左侧或主页点击【立即试用 / Try It Free】并停留在方案选择页。",
        "connected": "已连接 WebView2 调试目标：{url}",
        "binding": "正在调用 Apple 内部接口 updateUnidaysStatusSrv 绑定 UNiDAYS 学生身份...",
        "bind_ok": "✅ 学生资格绑定成功：{res}",
        "bind_warn": "⚠️ updateUnidaysStatusSrv 返回非预期结果（继续尝试触发结账）：{res}",
        "nav_sub": "正在确保页面位于纯净的 /music/subscribe 路由（剔除异常深链参数）...",
        "triggering": "正在选中大学生方案 (isStudent=true) 并调用 route:music/subscribe -> startListening...",
        "triggered": "✅ 已成功拉起 Apple Music 原生大学生订阅结账弹窗：{res}",
        "timeout_wv": "❌ 等待 finance-app WebView2 超时，请确认已在 Apple Music 中打开订阅方案弹窗。",
    },
    "en": {
        "wait_wv": "Waiting for Apple Music subscription sheet (finance-app.itunes.apple.com on port {port})...",
        "open_hint": "Tip: In Apple Music, click 'Try It Free' on Home so the subscription plans sheet is open.",
        "connected": "Connected to WebView2 target: {url}",
        "binding": "Calling updateUnidaysStatusSrv via Ember.$.ajax to bind UNiDAYS student status...",
        "bind_ok": "✅ Student status bound successfully: {res}",
        "bind_warn": "⚠️ updateUnidaysStatusSrv returned unexpected response (continuing to checkout): {res}",
        "nav_sub": "Ensuring WebView2 is on clean /music/subscribe route (without broken deep-link params)...",
        "triggering": "Selecting University Student offer (isStudent=true) and invoking startListening...",
        "triggered": "✅ Native Apple Music Student checkout triggered: {res}",
        "timeout_wv": "❌ Timed out waiting for finance-app WebView2. Please open the subscription sheet in Apple Music.",
    },
}


def extract_ud_s(raw: str) -> str:
    raw = raw.strip()
    if "ud_s=" in raw:
        parsed = urllib.parse.urlparse(raw if "://" in raw else "https://dummy/?" + raw)
        qs = urllib.parse.parse_qs(parsed.query)
        if "ud_s" in qs and qs["ud_s"]:
            return qs["ud_s"][0]
    return raw


def wait_for_finance_app_ws(port: int, lang: str, timeout_sec: int = 120) -> str:
    cdp_url = f"http://127.0.0.1:{port}/json"
    msgs = I18N[lang]
    print(msgs["wait_wv"].format(port=port))
    hint_shown = False
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(cdp_url, timeout=3) as resp:
                targets = json.loads(resp.read().decode("utf-8"))
            for t in targets:
                if t.get("type") == "page" and "finance-app.itunes.apple.com" in t.get("url", ""):
                    ws_url = t.get("webSocketDebuggerUrl")
                    if ws_url:
                        print(msgs["connected"].format(url=t.get("url")))
                        return ws_url
        except Exception:
            pass
        if not hint_shown:
            print(msgs["open_hint"])
            hint_shown = True
        time.sleep(1.5)
    raise RuntimeError(msgs["timeout_wv"])


def cdp_eval(ws: websocket.WebSocket, req_id: int, expr: str):
    ws.send(
        json.dumps(
            {
                "id": req_id,
                "method": "Runtime.evaluate",
                "params": {"expression": expr, "returnByValue": True, "awaitPromise": True},
            }
        )
    )
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == req_id:
            if "error" in msg:
                return {"cdpError": msg["error"]}
            r = msg.get("result", {})
            if "exceptionDetails" in r:
                return {"jsException": r["exceptionDetails"]}
            return r.get("result", {}).get("value")


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Apple Music + UNiDAYS One-Click Fix v{VERSION}")
    parser.add_argument("--ud-s", required=True, help="UNiDAYS ud_s token or full itmss:// callback URL")
    parser.add_argument("--port", type=int, default=9229, help="WebView2 CDP port (default: 9229)")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh", help="Output language (zh or en)")
    parser.add_argument("--checkout", action="store_true", help="Trigger student plan checkout after binding")
    args = parser.parse_args()

    msgs = I18N[args.lang]
    ud_s = extract_ud_s(args.ud_s)

    ws_url = wait_for_finance_app_ws(args.port, args.lang)
    ws = websocket.create_connection(ws_url, timeout=20)
    req_id = 1
    try:
        ws.send(json.dumps({"id": req_id, "method": "Runtime.enable", "params": {}}))
        ws.recv()
        req_id += 1

        # Wait until Ember container is initialized
        for _ in range(20):
            ready = cdp_eval(
                ws,
                req_id,
                "Boolean(window.Ember && Ember.Namespace && Ember.Namespace.NAMESPACES.find(n => n && n.__container__))",
            )
            req_id += 1
            if ready is True:
                break
            time.sleep(1.0)

        # 1. Bind ud_s via service:itunes-bag ('updateUnidaysStatusSrv') + Ember.$.ajax
        print(msgs["binding"])
        bind_expr = f"""(async () => {{
            const app = Ember.Namespace.NAMESPACES.find(n => n && n.__container__);
            const c = app.__container__;
            const bag = c.lookup('service:itunes-bag');
            const updateUrl = (bag && bag.getFromBag('updateUnidaysStatusSrv'))
                || 'https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus';
            const updateResp = await new Promise((resolve) => {{
                Ember.$.ajax({{
                    url: updateUrl,
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({{ ud_s: {json.dumps(ud_s)} }}),
                    success: (data, status, xhr) => resolve({{ ok: true, http: xhr && xhr.status, data }}),
                    error: (xhr, status, err) => resolve({{
                        ok: false,
                        http: xhr && xhr.status,
                        status,
                        err: String(err),
                        responseText: xhr && xhr.responseText
                    }})
                }});
            }});
            return {{ href: location.href, updateUrl, updateResp }};
        }})()"""
        bind_res = cdp_eval(ws, req_id, bind_expr)
        req_id += 1

        resp_obj = (bind_res or {}).get("updateResp") or {}
        if resp_obj.get("ok") and resp_obj.get("data", {}).get("status") == 0:
            print(msgs["bind_ok"].format(res=json.dumps(resp_obj, ensure_ascii=False)))
        else:
            print(msgs["bind_warn"].format(res=json.dumps(bind_res, ensure_ascii=False)))

        if args.checkout:
            # 2. Ensure we are on clean /music/subscribe without broken ud_h/ud_s/ud_t query params
            print(msgs["nav_sub"])
            cur_href = cdp_eval(ws, req_id, "location.href") or ""
            req_id += 1
            if "/music/subscribe" not in cur_href or "ud_" in cur_href:
                cdp_eval(
                    ws,
                    req_id,
                    "location.href = 'https://finance-app.itunes.apple.com/music/subscribe?app=music'",
                )
                req_id += 1
                time.sleep(3.0)
                for _ in range(20):
                    has_offers = cdp_eval(
                        ws,
                        req_id,
                        """(() => {
                            if (!window.Ember || !Ember.Namespace) return false;
                            const app = Ember.Namespace.NAMESPACES.find(n => n && n.__container__);
                            const ctrl = app && app.__container__.lookup('controller:music/subscribe');
                            return Boolean(ctrl && ctrl.get('selectedOffer'));
                        })()""",
                    )
                    req_id += 1
                    if has_offers is True:
                        break
                    time.sleep(1.0)

            # 3. Select University Student offer (isStudent === true) & call route.send('startListening')
            print(msgs["triggering"])
            checkout_expr = """(() => {
                const app = Ember.Namespace.NAMESPACES.find(n => n && n.__container__);
                const c = app.__container__;
                const ctrl = c.lookup('controller:music/subscribe');
                const route = c.lookup('route:music/subscribe');
                if (!ctrl || !route) {
                    return { error: 'controller or route music/subscribe not ready', href: location.href };
                }
                let sel = ctrl.get('selectedOffer');
                if (!sel || !sel.offer || !sel.offer.isStudent) {
                    const outlines = document.querySelectorAll('.outline-button');
                    for (let i = 0; i < outlines.length; i++) {
                        outlines[i].click();
                        sel = ctrl.get('selectedOffer');
                        if (sel && sel.offer && sel.offer.isStudent) break;
                    }
                }
                sel = ctrl.get('selectedOffer');
                if (!sel || !sel.offer || !sel.offer.isStudent) {
                    return { error: 'Could not select student offer', selected: sel && sel.offer };
                }
                route.send('startListening');
                return {
                    triggered: true,
                    offerId: sel.offer.id,
                    offerTitle: sel.offer.title,
                    isStudent: sel.offer.isStudent,
                    metricsBuyParams: sel.offer.metricsBuyParams
                };
            })()"""
            co_res = cdp_eval(ws, req_id, checkout_expr)
            print(msgs["triggered"].format(res=json.dumps(co_res, ensure_ascii=False)))
    finally:
        try:
            ws.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
