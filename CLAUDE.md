# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在本仓库工作时提供指引。

## 项目

异地远程协助电视的**自用工具**：帮助者通过**浏览器**访问自建 NAS 的 Web 页面，查看被协助者 Android 电视的屏幕快照并点按遥控。三端：

- **电视端**（`app/`，Kotlin）：常驻 App，无障碍截图/注入，开机自启，出站连 NAS
- **NAS 服务端**（`server/`，Python/FastAPI）：单账号登录、设备令牌、WebSocket 中继、SQLite
- **Web 前端**（`web/`，Vue3 + Element Plus）：登录、设备列表（含删除）、遥控页（快照 + 低帧率自动刷新 + 点按）

认证：浏览器账号密码（单账号/家庭，默认 `admin/admin123`）；电视端首次配置 NAS 地址 + 设备令牌后自动接入；**无配对码**。

详见 [CONTEXT.md](CONTEXT.md) 词汇表、[docs/adr/](docs/adr/) 决策、[docs/design/](docs/design/) 设计文档。

## 技术栈

| 端 | 技术 |
|---|---|
| 电视端 | Kotlin 原生（刻意无 AndroidX/Compose），OkHttp WebSocket；compileSdk 34 / minSdk 24 / targetSdk 30 |
| NAS 服务端 | Python 3.11+ / FastAPI / uvicorn / bcrypt / itsdangerous(session) / SQLite（标准库） |
| Web 前端 | Vue 3 + Vite + Element Plus（无 TS、无 router，单页状态切换） |

## 构建与运行

### NAS 服务端

```bash
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

- 首次启动自动建库并初始化账号（环境变量 `TVFLASH_ADMIN` / `TVFLASH_PASSWORD` / `TVFLASH_SECRET` / `TVFLASH_DATA` 覆盖）
- 创建电视设备令牌：`python -m app.make_device "客厅电视"`
- Web 构建产物放 `server/web_dist/`（`npm run build` 自动输出到此），由 FastAPI 托管 `/`

### Web 前端

```bash
cd web
npm install --registry=https://registry.npmmirror.com
npm run dev        # 开发（/api 与 /ws 代理到 127.0.0.1:8080）
npm run build      # 产物 → ../server/web_dist
```

### 电视端

Git Bash（Windows 程序需 `MSYS_NO_PATHCONV=1`）：

```bash
export JAVA_HOME="C:\Users\JSWPC2024101201\.jdks\temurin-17.0.12" MSYS_NO_PATHCONV=1
D:/Android/gradle-8.7/bin/gradle.bat assembleDebug
```

产物 `app/build/outputs/apk/debug/app-debug.apk`；`adb install -r` 后：开无障碍 → 填 NAS 地址+令牌 → 点「保存并连接」。

## 本机模拟器（重要坑，已踩过）

- AVD `tv30`（Android 11 / API 30），镜像 `system-images;android-30;google_apis;x86_64`
- 加速驱动已装 **AEHD**（`extras;google;Android_Emulator_Hypervisor_Driver`，需管理员运行 silent_install.bat）
- **必须用 ANGLE + 禁用 Vulkan 启动**，否则 Intel 核显上窗口反复卡死（Vulkan 是元凶，swiftshader 又慢到开不了机）：

```
emulator -avd tv30 -port 5556 -no-snapshot-load -no-boot-anim -gpu angle_indirect -feature -Vulkan
```

- AVD 已调为 1280x720 / 2G RAM / 无设备边框（`~/.android/avd/tv30.avd/config.ini`）
- 模拟器访问宿主机服务：`adb reverse tcp:8080 tcp:8080`，电视端地址填 `http://127.0.0.1:8080`
- adb 开无障碍：`settings put secure enabled_accessibility_services com.tvflash.remote/com.tvflash.remote.ScreenCaptureService` + `accessibility_enabled 1`
- 注意：`pm clear` 会重置无障碍且可能留下"崩溃标记"（dumpsys accessibility 可见 Crashed services），需**冷启动模拟器**清除；**不要用 guest reboot**（会卡死 system），要重启就杀进程冷启动

## 代码结构

```
app/  电视端
  MainActivity.kt            配置界面（地址/令牌、本地截图测试、状态每秒刷新）
  ScreenCaptureService.kt    无障碍：takeScreenshot / dispatchGesture / performGlobalAction
  TvClient.kt                WS 客户端：指令处理、快照缩放(≤1280)+q65、500ms 节流、断线 3s 重连
  KeepAliveService.kt        前台服务，持有 TvClient
  BootReceiver.kt            BOOT_COMPLETED 自启
  ConnectionState.kt         连接状态（Activity 每秒轮询显示）
server/  NAS 服务端
  app/main.py                FastAPI：REST(/api/*) + WS(/ws/web, /ws/tv) + 静态托管
  app/hub.py                 tv 连接表 + 浏览器订阅表 + 双向转发
  app/auth.py / db.py / config.py / make_device.py
  test_smoke.py / test_ws.py / test_refresh.py   REST 冒烟 / 中继单帧 / 慢刷 10 帧压测
web/  Web 前端
  src/views/Remote.vue       遥控页：自动刷新（串行循环/操作补帧/暂停恢复）、点按、系统键
  src/views/Devices.vue      设备列表（含删除）
  src/views/Login.vue        登录
  src/ws.js                  WebSocket 封装（指数退避重连，重连后自动补 open_session）
  src/api.js                 REST 封装
```

## 关键约束（重要）

- **坐标归一化（0~1）跨端传输**，电视端按自身分辨率换算；4K 真机与 720p 模拟器通用，绝不允许传绝对像素
- **截图与注入依赖无障碍服务**（takeScreenshot 需 API 30、dispatchGesture 需 API 24），一次启用重启仍有效；不要改用 MediaProjection（每次重启要授权，见 ADR-0003）
- **无 root 无法给第三方 App 注入方向键**，遥控 = 看快照点坐标 + 全局键（返回/主页/音量）
- 快照在电视端**缩放 ≤1280、JPEG q65、500ms 节流**；前端慢刷是**串行循环**（收到上一张才要下一张），流量 15~60KB/s
- 电视端 WS **断线 3s 自动重连**、Web WS 指数退避重连 —— 自用稳定性关键，别删
- 电源真关机/开机做不到，只能熄屏/待机
- 网络：两端出站连 NAS 中继，**不做 P2P**（ADR-0002）；开发期明文 ws + `usesCleartextTraffic`，上公网用 Caddy 反代 wss
- 目标设备 TCL 75V68M pro（Android 11/API 30）+ 海信；**真机尚未验证**（无障碍/自启/后台存活/4K 缩放），落地前必须跑 [docs/mvp-verification-checklist.md](docs/mvp-verification-checklist.md)

## 工作偏好

- **优先复用开源**，没有再自研（用户明确要求）
- 自用工具：KISS、少依赖、自托管（NAS）
- 设计先行：新功能先出设计文档（`docs/design/`）经用户确认再实现

## 参考文档

- [CONTEXT.md](CONTEXT.md) — 领域词汇表（帮助者/被协助端/设备令牌/会话/快照/慢刷/归一化坐标/中继）
- [docs/adr/](docs/adr/) — 架构决策（截图非实时流 / NAS 中继 / 无障碍基础）
- [docs/design/TECH_DESIGN.md](docs/design/TECH_DESIGN.md) — 整体技术方案
- [docs/design/auto-refresh-design.md](docs/design/auto-refresh-design.md) — 低帧率慢刷设计
- [docs/mvp-verification-checklist.md](docs/mvp-verification-checklist.md) — 真机五连验证清单
- [server/README.md](server/README.md) — 服务端运行/测试速览
