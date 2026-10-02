---
name: webapp-local-backend-bypass
description: 破解「强壳 exe + 浏览器前端 + 本地后端」型授权(Web 化的换肤器/外挂/工具)。触发词：本地后端、localhost 端口、Web 端授权、换肤器破解、V6Changer、Themida 外壳但走网页 UI、fetch 401 绕过、补丁前端、伪造登录、localStorage.isAuthenticated。
capabilities: [crack, web-reverse, local-api, anti-analysis]
---

# Web 化本地后端授权破解

目标形态：一个**强壳(Themida/VMProtect)的 exe** 其实只是「启动器 + 本地 HTTP 后端」，真正的 UI/授权展示在**浏览器网页**，真正干活(改内存/注入)在**本机后端**。网页卡登录/要卡密，但功能由本机服务端完成。

## 何时用 / 何时不用
- 用：exe 启动后监听本地端口 + 打开某网址；网页要账号/卡密才能用；exe 是强壳、常规解壳太贵。
- 不用：纯本地 GUI 授权(走 [[re-cracking]] / [[l-license]])；纯 Web 服务端鉴权(走 [[full-pentest]] / [[api-security]])。

## 核心判据(先做，5 分钟定性)
1. **加壳 exe 是不是「启动器+本地后端」**：`netstat -ano | grep <VS.exe 的 pid>` → 找 `LISTENING`。
2. **监听地址**：常见 `[::1]:8080`(**仅 IPv6 回环**)。用 `[::1]` 访问；`127.0.0.1` 会 `ECONNREFUSED`。
3. **枚举端点**：原始 socket 打 `/` 看 Server 标识；再逐个测。
4. **从厂商前端还原 API**：下载 `index-*.js`(Vite/Webpack bundle)，搜 `http://localhost`、引号里的 `/路径`、`fetch(`、`Authorization`、`localStorage`。拿到**端点表 + 载荷字段**。
5. **逐端点测鉴权**：同一批端点里极易出现「UI 挡登录，但核心端点(如 `/skin-changer`)未鉴权」。

## 三层绕过(按确定性从低到高)
1. **网络层**：注入 shim 劫持 `window.fetch`，把鉴权端点 `/ping` 的 `401` 改写成 `200`。
   - 只对「UI 依赖 HTTP 响应」的应用有效。
2. **逻辑层**：本地反代前端时对 bundle 打补丁：把 `localStorage.getItem("isAuthenticated")==="true"&&n(!0)` → `n(!0)`；把 `w.status===401&&(n(!1),localStorage.removeItem(...))` → `void 0`。
   - 对「登录态在 localStorage、只挂载读一次」的应用有效，确定性高。
3. **入口层**：伪造 `/login` 返回 `{success:true}`，**且短路不发请求**，让应用走**自己的登录成功流程**(`n(true)` + 写 localStorage)。
   - 最稳，绕过一切内部判定。

## 本地重托管模式(推荐成品形态)
用 `http.server` 反代官网：
- `/`(index.html)：取回后**注入** `<script src="/__unlock.js"></script>`(放 `<head>` 最前)；
- `*.js`：**打补丁**(上表两处)、去 `content-length`；
- 其余路径**透传**；
- 所有响应加 `Cache-Control: no-store`(否则补丁不生效)。

## 必做：「破坏性反调试」判定(用户最关心)
- 查**导入表**：有无 `SHFileOperation / FormatEx / ExitWindowsEx / LockWorkStation / BlockInput / DeviceIoControl(格式化)`。
- 命中的多半来自**打包进来的第三方工具**：`PECMD`(=盾牌.exe/DNS.exe，WinPE 工具)、`Geek Uninstaller`(=卸载工具.exe) → **归因而非误判**为主程序清盘反调试。
- 常见「反分析」实为**欺诈弹窗**：写 `%TEMP%\<rand>.vbs` 弹假告警(`ALERTA DE SEGURANCA`) + 跳官网。用 Process 监控捕获其 `CreateProcessW cmd /c echo MsgBox...` 即一目了然。**非破坏性**。

## 工具
- [[re-frida]] 动态：hook `CreateProcessW/WinExec/ShellExecute/send` 抓行为与网络。**注意宿主进程会被检测**(会报 `App detectado: <宿主名>` 并弹欺诈框)；改名或改被动抓包。
- 提权：目标 `requireAdministrator` → `Start-Process -Verb RunAs`；非提权 spawn 报 `0x2E4 ERROR_ELEVATION_REQUIRED`。
- 内存 dump(不注入)：可用 ctypes `ReadProcessMemory` 遍历模块区间(避免 frida 被检出)。

## 坑(血泪)
1. **别全局重写 `Storage.prototype.getItem`** → 自递归 → `RangeError: Maximum call stack size exceeded`，把应用整个卡死。只 hook `fetch`。
2. shim「等后端响应再改写」碰到**后端 `/login` 转发远程且不返回** → 永久「登录中…」。**对鉴权端点直接短路**(本地造响应，不发请求)。
3. 后端可能**只监听 IPv6**：把请求里的 `localhost` / `127.0.0.1` 统一改写成 `[::1]`。
4. 前端把登录态存 `localStorage` 且**只在挂载时读一次** → 只改网络响应无效，必须改前端逻辑或走 `/login` 成功流程。
5. **`.bat` 内容含中文 + cmd 用 GBK 解析** → 错当成命令，一屏「不是内部或外部命令」；且**别在 bat 里自提权**(原始窗口会立刻关闭=闪退)。对策：bat 内容**纯 ASCII**、结尾 `pause`、让目标自己弹 UAC。
6. **多窗口混淆**：官网页(卡登录、无标识)vs 本地页 → 给本地页加**顶部醒目横幅**区分，并在说明里写“认横幅”。
7. 反代前端务必 `no-store`，不然改动看不到。

## 交付清单
- 主：本地重托管 + 补丁前端 + fetch shim + 一键 `.bat`(放 exe 目录：提权→起前端→起后端→开页面)。
- 辅：油猴脚本 / 控制台一键脚本 / 命令行直连核心端点(自动化)。
- 报告：架构、鉴权端点表(公开/需登录/未鉴权)、反调试评估、破解原理、踩坑、复现命令。

## 复现骨架
```bash
# 1) 定性
tasklist | grep -i target.exe
netstat -ano | grep <pid>            # 找监听端口(注意 ::1)
# 2) 抓前端 bundle 还原 API
curl -sk https://<域名>/ | grep -oE 'src="[^"]+\.js"'
curl -sk https://<域名>/assets/index-*.js -o app.js
grep -aoE '/(api/)?[a-z-]+[a-z0-9/-]*' app.js | sort -u
# 3) 测未鉴权端点(注意用 [::1])
python -c "import socket;..."        # 或 curl -sk http://[::1]:8080/skin-changer -d '{}' -H 'Content-Type: application/json'
# 4) 起本地重托管前端(反代+注入+补丁) → 浏览器打开 127.0.0.1:8000
```
