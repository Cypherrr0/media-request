#!/usr/bin/env python3
"""CLI for the media request API. Stdlib only.

Config: MEDIA_REQ_API_KEY (env, or .env in the repo root). MEDIA_REQ_BASE_URL is optional.
Output: JSON on stdout. Errors: JSON on stdout + non-zero exit.
Exit codes: 0 ok, 1 HTTP/API error, 2 network error, 3 config error, 4 --wait timeout.
"""
import argparse, json, os, sys, time, urllib.error, urllib.parse, urllib.request

TERMINAL = {"available", "failed", "already_exists", "quota_exceeded", "dry_run_selected"}
STOP_WAIT = TERMINAL | {"not_found"}  # not_found retries server-side for days; stop polling and report it
REGIONS = ["anime_jp", "western", "cn", "other"]


def load_env():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def emit(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(code)


def call(method, path, params=None, body=None):
    base = (os.environ.get("MEDIA_REQ_BASE_URL") or "https://cy-media.duckdns.org/req").rstrip("/")
    key = os.environ.get("MEDIA_REQ_API_KEY", "")
    if not base or not key:
        emit({"error": "config", "message": "MEDIA_REQ_API_KEY 未配置"}, 3)
    url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode()).get("detail")
        except Exception:
            detail = None
        d = detail if isinstance(detail, dict) else {"message": str(detail or e.reason)}
        d.setdefault("error", {401: "unauthorized", 403: "forbidden", 404: "not_found", 429: "rate_limited"}.get(e.code, "http_error"))
        d["http_status"] = e.code
        emit(d, 1)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        emit({"error": "network", "message": f"无法连接服务: {getattr(e, 'reason', e)}"}, 2)


def main():
    load_env()
    p = argparse.ArgumentParser(prog="media_req.py", description="Media request API CLI")
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search", help="search movies/tv")
    s.add_argument("query"); s.add_argument("--type", choices=["movie", "tv"], default="movie")
    s.add_argument("--region", choices=REGIONS, default="other")
    r = sp.add_parser("request", help="request an item by id from search")
    r.add_argument("id"); r.add_argument("--region", choices=REGIONS, default="other")
    r.add_argument("--dry-run", action="store_true", help="select a release but do not download (if allowed for the key)")
    st = sp.add_parser("status", help="status of a request")
    st.add_argument("request_id"); st.add_argument("--wait", action="store_true", help="poll until a terminal state")
    st.add_argument("--interval", type=int, default=300, help="seconds between polls (default 300)")
    st.add_argument("--timeout", type=int, default=3600, help="max seconds to wait (default 3600)")
    sp.add_parser("list", help="list my requests and quota")
    a = p.parse_args()

    if a.cmd == "search":
        emit(call("GET", "/search", {"query": a.query, "type": a.type, "region": a.region}))
    if a.cmd == "request":
        res = call("POST", "/request", body={"id": a.id, "region": a.region, "dry_run": a.dry_run})
        emit(res, 1 if res.get("status") == "quota_exceeded" else 0)
    if a.cmd == "list":
        emit(call("GET", "/list"))
    if a.cmd == "status":
        path = "/status/" + urllib.parse.quote(a.request_id)
        res = call("GET", path)
        if not a.wait:
            emit(res)
        end = time.time() + a.timeout
        while res.get("status") not in STOP_WAIT:
            if time.time() + a.interval > end:
                res["wait"] = "timeout"; emit(res, 4)
            print(json.dumps({"status": res.get("status"), "message": res.get("message")}, ensure_ascii=False), file=sys.stderr, flush=True)
            time.sleep(max(5, a.interval))
            res = call("GET", path)
        emit(res, 1 if res.get("status") == "failed" else 0)


if __name__ == "__main__":
    main()
