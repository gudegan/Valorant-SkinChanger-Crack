// ==UserScript==
// @name         V6Changer 免卡密解锁 (完全破解)
// @namespace    v6crack
// @version      1.0
// @description  让 valorantskinchanger 网页端认为已登录, 绕过卡密/账号, 直接使用换肤 UI
// @match        https://valorantskinchanger.com.br/*
// @match        https://www.valorantskinchanger.com.br/*
// @run-at       document-start
// @grant        none
// ==/UserScript==
/*
 * 原理
 * ----
 * 网页用 `GET http://localhost:8080/ping` 的 200/401 决定是否"已登录"(写入 localStorage.isAuthenticated)。
 * 但真正下发皮肤的核心端点 `POST /skin-changer` 后端并不鉴权。
 * 本脚本在页面内把本地后端的鉴权端点重写为成功响应, 于是:
 *   界面直接进入"登录后"状态 -> 可自由选择皮肤 -> 点应用时调用的 /skin-changer 本来就不需要权限 -> 生效。
 *
 * 覆盖端点: /ping(解锁) /stats(仪表盘) /autolock/*  /pregame/match
 */
(function () {
  'use strict';
  const LOCAL = (u) => /localhost|127\.0\.0\.1|\[::1\]/.test(String(u || ''));
  const PORT = 8080;

  const json200 = (body) => new Response(JSON.stringify(body), {
    status: 200, headers: { 'Content-Type': 'application/json' }
  });

  const STATS = {
    display_name: 'Player#0000', level: 1, xp: 0,
    competitive_tier: 0, card: '', title: ''
  };

  function fakeFor(url) {
    if (!LOCAL(url)) return null;
    if (/\/ping(?:\?|$)/.test(url)) return { success: true, status: 'ok' };
    if (/\/stats(?:\?|$)/.test(url)) return STATS;
    if (/\/autolock\/(?:enable|disable|set-agent|set-region)/.test(url)) return { success: true };
    if (/\/pregame\/match(?:\?|$)/.test(url)) return { success: true, match: null };
    if (/\/test-pregame(?:\?|$)/.test(url)) return { success: true };
    if (/\/sound-kill\//.test(url)) return { success: true, files: [], count: 0 };
    return null;
  }

  // ---- fetch ----
  const _fetch = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    const url2 = url || (init && init.url) || '';
    let resp;
    try {
      resp = await _fetch(input, init);
    } catch (e) {
      const f = fakeFor(url || url2);
      if (f) { console.log('[V6Unlock] fetch 失败, 伪造 200 ->', url || url2); return json200(f); }
      throw e;
    }
    if (resp && resp.status === 401) {
      const f = fakeFor(url || url2);
      if (f) { console.log('[V6Unlock] 拦截 401 -> 200:', url || url2); return json200(f); }
    }
    return resp;
  };

  // ---- XHR (兜底) ----
  const _open = XMLHttpRequest.prototype.open;
  const _send = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__v6u = u; return _open.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function () {
    const self = this, f = fakeFor(self.__v6u);
    if (f) {
      self.addEventListener('readystatechange', function once() {
        if (self.readyState === 4) { self.removeEventListener('readystatechange', once); }
      });
      // 直接给出成功响应
      setTimeout(function () {
        try {
          Object.defineProperty(self, 'readyState', { value: 4, configurable: true });
          Object.defineProperty(self, 'status', { value: 200, configurable: true });
          Object.defineProperty(self, 'responseText', { value: JSON.stringify(f), configurable: true });
          Object.defineProperty(self, 'response', { value: JSON.stringify(f), configurable: true });
          if (typeof self.onreadystatechange === 'function') self.onreadystatechange();
          self.dispatchEvent(new Event('readystatechange'));
          self.dispatchEvent(new Event('load'));
        } catch (e) {}
      }, 0);
      return;
    }
    return _send.apply(this, arguments);
  };

  // ---- 立即置为已登录 ----
  try { localStorage.setItem('isAuthenticated', 'true'); } catch (e) {}
  window.addEventListener('load', function () {
    setTimeout(function () { try { window.dispatchEvent(new Event('focus')); } catch (e) {} }, 500);
  });
  console.log('%c[V6Unlock] 已加载: 本地后端鉴权端点将被伪造为成功, 界面应直接进入已登录状态', 'color:#0f0');
})();
