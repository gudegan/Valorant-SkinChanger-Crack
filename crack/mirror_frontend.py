#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6serve 本地镜像抓取器
-----------------------
在**能连上厂商域名**的机器上跑一次, 把前端静态资源抓到 static/ ,
之后 v6serve.py 就能完全离线托管页面(别人网络访问不了厂商域名也不会白屏)。

用法:
    python mirror_frontend.py            # 抓取/更新 static/
    python mirror_frontend.py --check    # 只检查 static/ 是否完整, 不联网

抓取内容: /  (index.html) 、/assets/*.js 、/assets/*.css 、/favicon.ico
         以及 html/js/css 里引用到的同域静态资源(会自动递归一层层补齐)。
"""
import urllib.request, urllib.parse, ssl, gzip, os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "static")
BASE = "https://valorantskinchanger.com.br"
SEED = ["/", "/assets/index-BEUy23wn.js", "/assets/index-D5LyRx9s.css", "/favicon.ico"]
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(path, timeout=25):
    req = urllib.request.Request(BASE + path, headers={
        "User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip", "Accept": "*/*"})
    r = urllib.request.urlopen(req, timeout=timeout, context=CTX)
    d = r.read()
    if "gzip" in r.headers.get("Content-Encoding", ""):
        try: d = gzip.decompress(d)
        except Exception: pass
    return r.status, r.headers.get("Content-Type", ""), d


def local_path(url_path):
    if url_path in ("/", "/index.html"):
        return os.path.join(OUT, "index.html")
    return os.path.join(OUT, url_path.lstrip("/").replace("/", os.sep))


def check():
    ok, miss = [], []
    for p in SEED:
        fp = local_path(p)
        (ok if os.path.isfile(fp) and os.path.getsize(fp) > 0 else miss).append(p)
    print("[check] 镜像目录: %s" % OUT)
    for p in ok:   print("  OK   %-34s %8d B" % (p, os.path.getsize(local_path(p))))
    for p in miss: print("  MISS %-34s (需要重新抓取)" % p)
    return not miss


def main():
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    seen, queue, meta = set(), list(SEED), {}
    while queue:
        p = queue.pop(0)
        if p in seen: continue
        seen.add(p)
        try:
            st, ct, d = get(p)
        except Exception as e:
            print("FAIL %-34s %s: %s" % (p, type(e).__name__, e)); continue
        fp = local_path(p)
        os.makedirs(os.path.dirname(fp) or ".", exist_ok=True)
        open(fp, "wb").write(d)
        meta[p] = {"status": st, "ctype": ct, "size": len(d)}
        print("OK   %-34s %s %8d %s" % (p, st, len(d), ct))
        text = d.decode("utf-8", "ignore") if (ct.startswith("text") or p.endswith((".js", ".css")) or p == "/") else None
        if not text: continue
        refs = set()
        for pat in [r'["\'](/(?:assets|fonts|images|img|static|media)/[A-Za-z0-9._@-]+)["\']',
                    r'url\(\s*["\']?(/(?:assets|fonts|images|img|static|media)/[A-Za-z0-9._@-]+)',
                    r'["\'](/?assets/[A-Za-z0-9._-]+\.(?:js|css|png|jpg|jpeg|svg|webp|woff2?|ttf|json|map))["\']']:
            refs |= set(re.findall(pat, text))
        for r_ in refs:
            if not r_.startswith("/"): r_ = "/" + r_
            if r_ not in seen: queue.append(r_)
    json.dump(meta, open(os.path.join(OUT, "_manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("--- 完成: %d 个文件 -> %s ---" % (len(meta), OUT))


if __name__ == "__main__":
    main()
