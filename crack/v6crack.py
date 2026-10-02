#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V6Changer 本地后端直连换肤工具 (授权实验室用途)
------------------------------------------------
目标: VS.exe 启动的本地后端 "V6Changer Server"  (http://[::1]:8080)
发现: 核心功能端点  POST /skin-changer  未鉴权  ->  无需卡密/账号即可下发皮肤配置。
本工具直接调用该端点(以及其它未鉴权端点), 绕过网页端登录授权。

用法:
  python v6crack.py health
  python v6crack.py search Vandal Prime            # 查皮肤(可用 valorant-api.com)
  python v6crack.py set Vandal=Prime Ghost=Reaver  # 下发一整套皮肤
  python v6crack.py set Vandal=Prime --chroma 金色 --level 4 --kill-sound --finisher
  python v6crack.py raw '{"vandal":"Prime_Vandal","vandalselect":true}'
"""
import sys, json, socket, argparse, urllib.request

HOST = "::1"
PORT = 8080

WEAPON_KEYS = {
    "ares": "ares", "bucky": "bucky", "bulldog": "bulldog", "classic": "classic",
    "frenzy": "frenzy", "ghost": "ghost", "guardian": "guardian", "judge": "judge",
    "marshal": "marshal", "melee": "melee", "odin": "odin", "operator": "operator",
    "outlaw": "outlaw", "phantom": "phantom", "sheriff": "sheriff", "shorty": "shorty",
    "spectre": "spectre", "stinger": "stinger", "vandal": "vandal",
}


def request(method, path, obj=None, timeout=8):
    """Raw HTTP/1.1 request to the local bridge (IPv6 loopback)."""
    s = socket.create_connection((HOST, PORT), timeout)
    hdr = {
        "Host": "localhost:%d" % PORT,
        "Origin": "https://valorantskinchanger.com.br",
        "Referer": "https://valorantskinchanger.com.br/",
        "User-Agent": "Mozilla/5.0",
    }
    body = json.dumps(obj).encode() if obj is not None else b""
    if body:
        hdr["Content-Type"] = "application/json"
        hdr["Content-Length"] = str(len(body))
    req = ("%s %s HTTP/1.1\r\n" % (method, path) + "".join("%s: %s\r\n" % kv for kv in hdr.items()) + "\r\n").encode()
    s.sendall(req + body)
    data = b""
    try:
        while True:
            c = s.recv(8192)
            if not c:
                break
            data += c
    except Exception:
        pass
    s.close()
    text = data.decode("utf-8", "ignore")
    head, _, resp = text.partition("\r\n\r\n")
    status = head.splitlines()[0] if head else ""
    try:
        js = json.loads(resp)
    except Exception:
        js = resp
    return status, js, head


def health():
    st, js, _ = request("GET", "/health")
    print("[health]", st, js)
    st, js, _ = request("GET", "/skin-changer/configs")
    print("[configs]", st, js)
    return st


# ---- optional: pull real asset names from valorant-api.com ----
def fetch_weapons():
    url = "https://valorant-api.com/v1/weapons"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)["data"]


def resolve(weapon_display, skin_name):
    """Return (skin_asset, chroma_assets, levels) for a weapon+skin name."""
    for w in fetch_weapons():
        if w["displayName"].lower() != weapon_display.lower():
            continue
        skins = w.get("skins", [])
        # 优先精确/前缀匹配, 再退回子串匹配
        order = ([s for s in skins if s["displayName"].lower() == skin_name.lower()]
                 + [s for s in skins if s["displayName"].lower().startswith(skin_name.lower())]
                 + [s for s in skins if skin_name.lower() in s["displayName"].lower()])
        for sk in order:
                base = sk.get("assetPath", "").rstrip("/").split("/")[-1]
                chromas = {c["displayName"]: c["assetPath"].rstrip("/").split("/")[-1]
                           for c in sk.get("chromas", [])}
                levels = [l["assetPath"].rstrip("/").split("/")[-1] for l in sk.get("levels", [])]
                return base, chromas, levels
    return None, {}, []


def build_payload(pairs, chroma=None, level=None, kill_sound=False, finisher=False, buddy=None):
    m = {"loadoutName": "v6crack"}
    for display, skin in pairs:
        key = WEAPON_KEYS.get(display.lower())
        if not key:
            print("  ! 未知武器:", display); continue
        base, chromas, levels = resolve(display, skin)
        if not base:
            print("  ! 找不到皮肤 %s=%s (仍按原名下发)" % (display, skin))
            base = skin
        m[key] = base
        m[key + "select"] = True
        if chroma:
            want = chromas.get(chroma) or next((v for k, v in chromas.items() if chroma.lower() in k.lower()), None)
            if want:
                m[key + "chroma"] = want
                print("  + %s chroma=%s" % (display, want))
        m[key + "level"] = int(level) if level else max(1, len(levels) or 1)
    m["buddieEnabled"] = bool(buddy)
    m["buddy"] = buddy if isinstance(buddy, int) else 0
    m["finisherEnabled"] = bool(finisher)
    m["finisherLastKillOnly"] = False
    m["soundKillEnabled"] = bool(kill_sound)
    m["soundKill"] = bool(kill_sound)
    m["soundKillLastKillOnly"] = False
    return m


def main():
    ap = argparse.ArgumentParser(description="V6Changer 本地后端直连换肤(绕过授权)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("health")
    p_set = sub.add_parser("set")
    p_set.add_argument("pairs", nargs="+", help="Weapon=Skin 例如 Vandal=Prime")
    p_set.add_argument("--chroma", default=None)
    p_set.add_argument("--level", default=None)
    p_set.add_argument("--kill-sound", action="store_true")
    p_set.add_argument("--finisher", action="store_true")
    p_set.add_argument("--buddy", default=None)
    p_raw = sub.add_parser("raw")
    p_raw.add_argument("json")
    p_s = sub.add_parser("search")
    p_s.add_argument("weapon")
    p_s.add_argument("skin")
    args = ap.parse_args()

    if args.cmd == "health":
        health()
    elif args.cmd == "raw":
        payload = json.loads(args.json)
        print("[POST /skin-changer]", request("POST", "/skin-changer", payload)[:2])
    elif args.cmd == "set":
        pairs = [tuple(x.split("=", 1)) for x in args.pairs]
        payload = build_payload(pairs, args.chroma, args.level, args.kill_sound, args.finisher, args.buddy)
        print("payload:", json.dumps(payload, ensure_ascii=False))
        st, js, _ = request("POST", "/skin-changer", payload)
        print("[POST /skin-changer]", st, js)
    elif args.cmd == "search":
        base, chromas, levels = resolve(args.weapon, args.skin)
        print("asset:", base)
        print("chromas:", list(chromas.keys()))
        print("levels:", len(levels))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
