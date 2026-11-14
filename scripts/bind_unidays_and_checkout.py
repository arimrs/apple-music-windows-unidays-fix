#!/usr/bin/env python3
"""
Bind a verified UNiDAYS `ud_s` token directly inside Apple Music's WebView2
(`finance-app`) via CDP and optionally trigger the University Student offer
checkout without broken `itmss://` deep-link parameters.

Prerequisites:
  1. Enable WebView2 remote debugging on port 9229 (`enable_webview2_cdp.ps1 -Enable`).
  2. Open Apple Music on Windows and navigate to the subscription / account sheet
     so `msedgewebview2.exe` loads `https://finance-app.itunes.apple.com/...`.
  3. Obtain `ud_s` from your authenticated UNiDAYS redirect URL:
     `itmss://itunes.apple.com/studentSubscriptionOffers?...&ud_s=<UD_S_TOKEN>&...`
  4. `pip install websocket-client`
"""

import argparse
import json
import sys
import urllib.request
import websocket  # pip install websocket-client


CDP_URL = "http://127.0.0.1:9229/json"
STUDENT_ADAM_ID = "1608221191"
STUDENT_OFFER_NAME = "com.apple.music.AppleMusicStudent"


def find_finance_app_ws(cdp_url: str = CDP_URL) -> str:
    with urllib.request.urlopen(cdp_url, timeout=5) as resp:
        targets = json.loads(resp.read().decode("utf-8"))
    for t in targets:
        url = t.get("url", "")
        if "finance-app.itunes.apple.com" in url and t.get("webSocketDebuggerUrl"):
            return t["webSocketDebuggerUrl"]
    raise RuntimeError(
        "No finance-app.itunes.apple.com WebView2 target found on port 9229. "
        "Open the Apple Music subscription/account view first."
    )


def cdp_eval(ws: websocket.WebSocket, expression: str, call_id: int = 1):
    payload = {
        "id": call_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expression,
            "awaitPromise": True,
            "returnByValue": True,
        },
    }
    ws.send(json.dumps(payload))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == call_id:
            if "exceptionDetails" in msg.get("result", {}):
                raise RuntimeError(json.dumps(msg["result"]["exceptionDetails"], ensure_ascii=False))
            return msg.get("result", {}).get("result", {}).get("value")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind UNiDAYS ud_s token via Apple Music WebView2 CDP")
    parser.add_argument("--ud-s", required=True, help="UNiDAYS ud_s token from studentSubscriptionOffers URL")
    parser.add_argument("--checkout", action="store_true", help="Also trigger student plan checkout (startListening)")
    args = parser.parse_args()

    ws_url = find_finance_app_ws()
    ws = websocket.create_connection(ws_url, timeout=15)
    try:
        bind_js = f"""
        (async () => {{
            const resp = await fetch("https://p52-buy.itunes.apple.com/commerce/student/updateUnidaysStatus", {{
                method: "POST",
                credentials: "include",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ ud_s: {json.dumps(args.ud_s)} }})
            }});
            const data = await resp.json().catch(() => ({{}}));
            return {{ ok: resp.ok, status: resp.status, data }};
        }})()
        """
        bind_res = cdp_eval(ws, bind_js, call_id=1)
        print("updateUnidaysStatus result:", json.dumps(bind_res, ensure_ascii=False))

        if args.checkout:
            checkout_js = f"""
            (() => {{
                const app = window.FinanceApp || window.App;
                if (!app || !app.__container__) return {{ error: "Ember container not found" }};
                const route = app.__container__.lookup("route:music/subscribe");
                if (!route) return {{ error: "route:music/subscribe not loaded" }};
                route.send("startListening", {{
                    salableAdamId: {json.dumps(STUDENT_ADAM_ID)},
                    offerName: {json.dumps(STUDENT_OFFER_NAME)}
                }});
                return {{ triggered: true }};
            }})()
            """
            co_res = cdp_eval(ws, checkout_js, call_id=2)
            print("checkout trigger result:", json.dumps(co_res, ensure_ascii=False))
    finally:
        ws.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
