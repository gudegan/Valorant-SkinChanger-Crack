/*
 * V6Changer 网页端一键绕过 (浏览器控制台脚本 / 油猴脚本)
 * 在 https://valorantskinchanger.com.br/ 页面按 F12 → Console → 粘贴执行
 *
 * 原理: 网页用 /ping 的 401 判断是否登录; 但真正下发皮肤的核心端点
 *       POST /skin-changer 在后端未鉴权。本脚本:
 *         1) 劫持 fetch, 把本地后端 /ping 的 401 改写为 200 -> 界面直接解锁(无需卡密)
 *         2) 其余请求原样转发
 *       以及提供 window.V6Crack.set({...}) 直接下发皮肤。
 */
(function () {
  const PORT = 8080;
  const isLocal = (u) => /localhost|127\.0\.0\.1|\[::1\]/.test(String(u));

  // 1) 把本地后端的鉴权端点 401 改写为 200, 让界面认为已授权(解锁 UI)
  const _fetch = window.fetch.bind(window);
  const FAKE = (u, s) => {
    if (/\/ping(?:\?|$)/.test(u)) return { success: true, status: "ok" };
    if (/\/stats(?:\?|$)/.test(u)) return { display_name: "Player#0000", level: 1, xp: 0, competitive_tier: 0, card: "", title: "" };
    if (/\/autolock\/(?:enable|disable|set-agent|set-region)/.test(u)) return { success: true };
    if (/\/pregame\/match(?:\?|$)/.test(u)) return { success: true, match: null };
    if (/\/test-pregame(?:\?|$)/.test(u)) return { success: true };
    if (/\/sound-kill\//.test(u)) return { success: true, files: [], count: 0 };
    return null;
  };
  window.fetch = async function (input, init) {
    const url = typeof input === "string" ? input : (input && input.url) || "";
    let resp;
    try { resp = await _fetch(input, init); }
    catch (e) { const f = isLocal(url) ? FAKE(url) : null; if (f) return new Response(JSON.stringify(f), { status: 200, headers: { "Content-Type": "application/json" } }); throw e; }
    if (isLocal(url) && resp.status === 401) {
      const f = FAKE(url);
      if (f) return new Response(JSON.stringify(f), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    return resp;
  };
  const _open = XMLHttpRequest.prototype.open; // 兼容 XHR
  XMLHttpRequest.prototype.open = function (m, u, ...rest) {
    this.__v6url = u; return _open.call(this, m, u, ...rest);
  };

  // 2) 直接下发皮肤的工具
  async function set(payload) {
    const url = `http://localhost:${PORT}/skin-changer`;
    const r = await _fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Origin: location.origin },
      body: JSON.stringify(payload),
    });
    const j = await r.json().catch(() => ({}));
    console.log("[V6Crack] send ->", r.status, j);
    return j;
  }

  // 3) 便捷: 按 武器=皮肤资源名 生成并下发 (资源名形如 Prime_Vandal_PrimaryAsset)
  async function apply(map, opts = {}) {
    const m = { loadoutName: opts.name || "v6crack" };
    const keys = ["ares","bucky","bulldog","classic","frenzy","ghost","guardian","judge","marshal",
      "melee","odin","operator","outlaw","phantom","sheriff","shorty","spectre","stinger","vandal"];
    for (const k of Object.keys(map)) {
      const key = k.toLowerCase();
      if (!keys.includes(key)) continue;
      m[key] = map[k];
      m[key + "select"] = true;
      m[key + "level"] = opts.level || 4;
      if (opts.chroma) m[key + "chroma"] = opts.chroma;
    }
    m.buddieEnabled = !!opts.buddy; m.buddy = opts.buddy | 0;
    m.finisherEnabled = !!opts.finisher; m.finisherLastKillOnly = false;
    m.soundKillEnabled = !!opts.killSound; m.soundKill = !!opts.killSound; m.soundKillLastKillOnly = false;
    return set(m);
  }

  window.V6Crack = { set, apply };
  localStorage.setItem("isAuthenticated", "true");
  console.log("%c[V6Crack] 已注入: 界面已解锁; 用 V6Crack.apply({vandal:'Prime_Vandal_PrimaryAsset', phantom:'Prime_Phantom_PrimaryAsset'}) 一键换肤",
    "color:#0f0");
})();
