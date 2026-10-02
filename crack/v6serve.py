#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V6Changer 本地免卡密前端 (自包含破解)
--------------------------------------
把厂商网页在本地重新托管, 并在页面里注入"解锁 shim":
  - 把本地后端 http://localhost:8080 的鉴权端点(/ping 等)的 401 改写成 200
  - 页面因此直接进入"已登录"状态; 应用皮肤时调用的 /skin-changer 本就未鉴权 -> 生效
静态资源(/assets/*)与其它路径反向代理到真实站点, 保证 UI 完整。

用法:
  python v6serve.py               # 默认监听 127.0.0.1:8000
 然后浏览器打开 http://127.0.0.1:8000/
前置: 先运行 VS.exe (本地后端 [::1]:8080 在线)。
"""
import http.server, socketserver, urllib.request, ssl, sys, gzip, io

BASE = "https://valorantskinchanger.com.br"
LISTEN = ("127.0.0.1", 8000)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

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
    # AuthProvider 挂载时无条件下载为已登录
    ('localStorage.getItem("isAuthenticated")==="true"&&n(!0)', 'n(!0)'),
    # 屏蔽 /ping 401 触发的“登出”
    ('w.status===401&&(n(!1),localStorage.removeItem("isAuthenticated"))', 'void 0'),
]

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


PATCHES = [
    # AuthProvider 挂载时无条件下载为已登录
    ('localStorage.getItem("isAuthenticated")==="true"&&n(!0)', 'n(!0)'),
    # 屏蔽 /ping 401 触发的“登出”
    ('w.status===401&&(n(!1),localStorage.removeItem("isAuthenticated"))', 'void 0'),
]

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
    r = urllib.request.urlopen(req, timeout=25, context=CTX)
    data = r.read()
    enc = r.headers.get("Content-Encoding", "")
    if "gzip" in enc:
        try: data = gzip.decompress(data)
        except Exception: pass
    return r.status, dict(r.headers), data

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        sys.stderr.write("[serve] %s\n" % (a[0] % a[1:]))

    def _send(self, status, headers, body):
        self.send_response(status)
        for k, v in headers.items():
            if k.lower() in ("content-encoding", "content-length", "transfer-encoding", "connection",
                             "cache-control", "etag", "expires", "last-modified", "age", "vary"): continue
            self.send_header(k, v)
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try: self.wfile.write(body)
        except Exception: pass

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/__unlock.js":
            self._send(200, {"Content-Type": "application/javascript; charset=utf-8"}, UNLOCK_JS.encode())
            return
        try:
            if p in ("/", "/index.html"):
                st, hd, body = fetch("/")
                html = body.decode("utf-8", "ignore")
                shim = '<script src="/__unlock.js"></script>'
                if "<head>" in html: html = html.replace("<head>", "<head>" + shim, 1)
                else: html = shim + html
                self._send(200, {"Content-Type": "text/html; charset=utf-8"}, html.encode("utf-8"))
                return
            st, hd, body = fetch(self.path)
            if p.endswith(".js"):
                body = patch_js(body)
                hd = dict(hd); hd.pop("Content-Length", None)
            self._send(st, hd, body)
        except Exception as e:
            self._send(502, {"Content-Type": "text/plain"}, ("proxy error: %s" % e).encode())

    do_POST = do_GET
    do_OPTIONS = do_GET

if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(LISTEN, H) as httpd:
        print("V6Changer local unlock UI -> http://%s:%d/" % LISTEN)
        httpd.serve_forever()
