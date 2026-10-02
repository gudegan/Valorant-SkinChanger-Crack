#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V6Changer 本地免卡密前端 (自包含破解 · 离线镜像版)
----------------------------------------------------
把厂商网页在**本地**托管(static/ 里是抓好的前端镜像), 不再依赖运行时联网:

  1. 页面本体(index.html + /assets/*.js + /assets/*.css)从 static/ 本地读 -> 断网也能开;
  2. 注入"解锁 shim"(/__unlock.js):
       - 把本地后端 http://localhost:8080 的鉴权端点(/ping 等)的 401 改写成 200
       - 页面因此直接进入"已登录"状态; 应用皮肤时调用的 /skin-changer 本就未鉴权 -> 生效
  3. static/ 里没有的路径才回源真实站点(默认 8s 超时, 失败给友好提示页, 不再抛裸异常)。

用法:
  python v6serve.py               # 默认监听 127.0.0.1:8000
 然后浏览器打开 http://127.0.0.1:8000/
前置: 先运行 VS.exe (本地后端 [::1]:8080 在线)。
"""
import http.server, socketserver, urllib.request, ssl, sys, gzip, os, mimetypes, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
MIRROR = os.path.join(HERE, "static")          # 本地前端镜像目录
BASE = "https://valorantskinchanger.com.br"    # 仅在镜像缺文件时才回源
LISTEN = ("127.0.0.1", 8000)
REMOTE_TIMEOUT = 8                             # 回源超时(秒), 之前 25s 会让页面长时间空白
ONLINE_FALLBACK = True                         # 镜像缺文件时是否尝试回源

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".map": "application/json; charset=utf-8",
}

UNLOCK_JS = r"""
(function(){
  if (window.__V6_UNLOCK__) return; window.__V6_UNLOCK__=true;
  function isLocal(u){return /localhost|127\.0\.0\.1|\[::1\]/.test(String(u||''));}
  var S={display_name:'Player#0000',level:1,xp:0,competitive_tier:0,card:'',title:''};
  function fake(u){
    if(!isLocal(u)) return null;
    if(/\/ping(?:\?|$)/.test(u)) return {success:true,status:'ok'};
    if(/\/stats(?:\?|$)/.test(u)) return S;
    if(/\/autolock\/(?:enable|disable|set-agent|set-region)/.test(u)) return {success:true};
    if(/\/pregame\/match(?:\?|$)/.test(u)) return {success:true,match:null};
    if(/\/test-pregame(?:\?|$)/.test(u)) return {success:true};
    if(/\/sound-kill\//.test(u)) return {success:true,files:[],count:0};
    if(/\/login(?:\?|$)/.test(u)) return {success:true,message:'Login successful'};
    if(/\/register(?:\?|$)/.test(u)) return {success:true,message:'Successfully registered, login now!'};
    if(/\/renew(?:\?|$)/.test(u)) return {success:true,message:'Key successfully redeemed, login now'};
    return null;
  }
  function j200(b){return new Response(JSON.stringify(b),{status:200,headers:{'Content-Type':'application/json'}});}
  var of=window.fetch?window.fetch.bind(window):null;
  if(of){ window.fetch=function(i,init){
    var u=typeof i==='string'?i:((i&&i.url)||'');
    var f=fake(u);
    if(f) return Promise.resolve(j200(f));   // 直接短路, 不请求后端(避免后端转发远程导致挂起)
    // 后端只监听 IPv6 回环; 统一把 localhost/127.0.0.1 改写成 [::1] 防止 IPv4 解析被拒
    var u2=u.replace(/^http:\/\/(localhost|127\.0\.0\.1)(:8080)/i,'http://[::1]$2');
    if(u2!==u&&typeof i==='string') i=u2;
    return of(i,init);
  };}
  try{localStorage.setItem('isAuthenticated','true');}catch(e){}
  setTimeout(function(){try{window.dispatchEvent(new Event('focus'));}catch(e){}},300);
  function badge(){
    try{
      var d=document.createElement('div'); d.id='__v6badge';
      d.style.cssText='position:fixed;left:50%;top:0;transform:translateX(-50%);z-index:2147483647;background:#e11;color:#fff;font:bold 15px/24px sans-serif;padding:6px 18px;border-radius:0 0 8px 8px;pointer-events:none;box-shadow:0 2px 8px rgba(0,0,0,.4)';
      d.textContent='✔ V6 破解版已生效（免卡密 · 本地补丁页）';
      document.documentElement.appendChild(d);
    }catch(e){}
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',badge); else badge();
  try{console.log('%c[V6Unlock] active (local serve)','color:#0f0');}catch(e){}
})();
"""

PATCHES = [
    # AuthProvider 挂载时无条件视为已登录
    ('localStorage.getItem("isAuthenticated")==="true"&&n(!0)', 'n(!0)'),
    # 屏蔽 /ping 401 触发的“登出”
    ('w.status===401&&(n(!1),localStorage.removeItem("isAuthenticated"))', 'void 0'),
]

SHIM = b'<script src="/__unlock.js"></script>'

OFFLINE_HTML = """<!doctype html><meta charset="utf-8">
<title>V6 本地补丁页 · 离线</title>
<style>body{background:#111;color:#eee;font:15px/1.7 sans-serif;padding:40px;max-width:760px;margin:0 auto}
code{background:#222;padding:2px 6px;border-radius:4px}h1{font-size:19px}</style>
<h1>本地前端缺文件,已进入离线模式</h1>
<p>请求: <code>%s</code></p>
<p>原因: 该资源不在本地镜像 <code>%s</code> 里, 回源 <code>%s</code> 也失败了
(常见: 当前网络访问不了厂商域名 —— TLS 握手超时)。</p>
<p>处理: 在能连上厂商域名的机器上重新抓一次镜像, 把 <code>static\\</code> 整个目录一起发过去;
或确认 <code>static\\index.html</code>、<code>static\\assets\\</code> 没被杀软/解压工具漏掉。</p>
"""


def patch_js(data: bytes) -> bytes:
    try:
        s = data.decode("utf-8")
    except Exception:
        return data
    hit = 0
    for a, b in PATCHES:
        if a in s:
            s = s.replace(a, b)
            hit += 1
    if hit:
        sys.stderr.write("[serve] patched %d auth sites in JS bundle\n" % hit)
    return s.encode("utf-8")


def fetch(path, extra_headers=None):
    req = urllib.request.Request(BASE + path, headers={
        "User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip",
        "Accept": "*/*", **(extra_headers or {})
    })
    r = urllib.request.urlopen(req, timeout=REMOTE_TIMEOUT, context=CTX)
    data = r.read()
    enc = r.headers.get("Content-Encoding", "")
    if "gzip" in enc:
        try: data = gzip.decompress(data)
        except Exception: pass
    return r.status, dict(r.headers), data


def mime_of(path):
    return MIME.get(os.path.splitext(path)[1].lower()) or \
           mimetypes.guess_type(path)[0] or "application/octet-stream"


def mirror_file(url_path):
    """把 URL 路径映射到 static/ 下的本地文件; 不存在返回 None。带目录穿越防护。"""
    rel = "index.html" if url_path in ("/", "/index.html") else url_path.lstrip("/")
    rel = urllib.parse.unquote(rel)
    fp = os.path.normpath(os.path.join(MIRROR, rel.replace("/", os.sep)))
    root = os.path.abspath(MIRROR) + os.sep
    if not (os.path.abspath(fp) + os.sep).startswith(root):
        return None
    return fp if os.path.isfile(fp) else None


class H(http.server.BaseHTTPRequestHandler):
    server_version = "v6serve/2.0"

    def log_message(self, *a):
        sys.stderr.write("[serve] %s\n" % (a[0] % a[1:]))

    def _send(self, status, headers, body):
        self.send_response(status)
        for k, v in headers.items():
            if k.lower() in ("content-encoding", "content-length", "transfer-encoding", "connection",
                             "cache-control", "etag", "expires", "last-modified", "age", "vary"):
                continue
            self.send_header(k, v)
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try: self.wfile.write(body)
        except Exception: pass

    def _html(self, data: bytes) -> bytes:
        if b"/__unlock.js" in data:
            return data
        if b"<head>" in data:
            return data.replace(b"<head>", b"<head>" + SHIM, 1)
        return SHIM + data

    def _serve_local(self, fp, url_path):
        data = open(fp, "rb").read()
        ext = os.path.splitext(fp)[1].lower()
        if ext == ".html":
            data = self._html(data)
        elif ext in (".js", ".mjs"):
            data = patch_js(data)
        self._send(200, {"Content-Type": mime_of(fp)}, data)

    def do_GET(self):
        p = urllib.parse.urlsplit(self.path).path
        if p == "/__unlock.js":
            self._send(200, {"Content-Type": "application/javascript; charset=utf-8"}, UNLOCK_JS.encode())
            return

        # 1) 本地镜像优先(离线可用)
        fp = mirror_file(p)
        if fp:
            try:
                self._serve_local(fp, p)
                return
            except Exception as e:
                sys.stderr.write("[serve] local read fail %s: %s\n" % (p, e))

        # 2) 回源(仅镜像缺文件时)
        if ONLINE_FALLBACK:
            try:
                st, hd, body = fetch(self.path)
                if p.endswith((".js", ".mjs")):
                    body = patch_js(body)
                if p.endswith(".html") or p in ("/", "/index.html"):
                    body = self._html(body)
                hd = dict(hd); hd.pop("Content-Length", None)
                self._send(st, hd, body)
                return
            except Exception as e:
                sys.stderr.write("[serve] remote fail %s: %s\n" % (p, e))

        # 3) SPA 路由(非资源类路径) -> 本地 index.html, 保证页面能渲染
        if not p.startswith("/assets/") and "." not in os.path.basename(p):
            idx = mirror_file("/index.html")
            if idx:
                self._serve_local(idx, "/index.html")
                return

        # 4) 兜底: 友好提示页(不再返回裸 "proxy error ... timeoute")
        html = OFFLINE_HTML % (p, MIRROR, BASE)
        self._send(404, {"Content-Type": "text/html; charset=utf-8"}, html.encode("utf-8"))

    do_POST = do_GET
    do_OPTIONS = do_GET


if __name__ == "__main__":
    n_mirror = 0
    for _dp, _dn, _fn in os.walk(MIRROR):
        n_mirror += len(_fn)
    if n_mirror:
        print("[v6serve] local mirror: %s (%d files) -> 离线可用" % (MIRROR, n_mirror))
    else:
        print("[v6serve] !! 没有本地镜像 %s, 只能实时回源 %s (别人网络不通就会出现空白页)" % (MIRROR, BASE))
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(LISTEN, H) as httpd:
        print("V6Changer local unlock UI -> http://%s:%d/" % LISTEN)
        httpd.serve_forever()
