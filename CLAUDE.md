# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在本仓库工作时提供指引。

## 项目

异地远程协助电视的**自用工具**：帮助者用手机（帮助端）远程操作被协助者的 Android 电视（被协助端）。核心流程：配对码配对 → 看屏幕快照 → 点按遥控电视。服务器是自建 **NAS**（配对撮合 + 数据中继）。

当前仓库只有「**电视端最小验证 App**」骨架（`app/`），用于在 Android 11（API 30）的 AVD 或真机上验证四条链路：无障碍开启、截图、点击注入、开机自启。

详见 [CONTEXT.md](CONTEXT.md) 词汇表与 [docs/adr/](docs/adr/) 架构决策。

## 技术栈

- 语言：Kotlin（两端均原生；本仓库为电视端）
- 构建：Gradle 8.7 + AGP 8.5.2 + Kotlin 1.9.24 + JDK 17
- Android：compileSdk 34 / minSdk 24 / targetSdk 30
- 骨架阶段**刻意零 AndroidX、不用 Compose**：用原生 `android.*` API + XML View，减少版本匹配坑

## 构建与安装

开发环境（原生 Android 工具链，**不使用第三方模拟器**）：
- **Android Studio**：安装到 `D:\Android\AndroidStudio`（安装向导中选择该空文件夹）
- JDK：`C:\Users\JSWPC2024101201\.jdks\temurin-17.0.12`
- Gradle：`D:\Android\gradle-8.7\bin\gradle.bat`
- Android SDK：`D:\Android\Sdk`（已在 `local.properties` 中指定；Android Studio 首次启动把 SDK 指向这里，复用已装的 platform/build-tools）
- 运行目标：Android Studio 的 **AVD（API 30）** 或真机（TCL 75V68M pro / 海信）

Git Bash 下构建（Windows 程序需 `MSYS_NO_PATHCONV=1`）：

```bash
export JAVA_HOME="C:\Users\JSWPC2024101201\.jdks\temurin-17.0.12" MSYS_NO_PATHCONV=1
D:/Android/gradle-8.7/bin/gradle.bat assembleDebug
```

产物：`app/build/outputs/apk/debug/app-debug.apk`

安装到模拟器：

```bash
D:/Android/Sdk/platform-tools/adb.exe devices
D:/Android/Sdk/platform-tools/adb.exe -s <serial> install -r app/build/outputs/apk/debug/app-debug.apk
```

## 代码结构

- `MainActivity.kt` — 测试界面：显示配对码、截图、测试点击
- `ScreenCaptureService.kt` — 无障碍服务：`takeScreenshot`（API 30+）截图、`dispatchGesture` 注入点击
- `KeepAliveService.kt` — 前台服务，常驻
- `BootReceiver.kt` — `BOOT_COMPLETED` 开机自启
- `res/xml/accessibility_service_config.xml` — 无障碍能力声明（`canTakeScreenshot`、`canPerformGestures`）

## 关键约束（重要）

- **坐标必须用归一化相对坐标（0.0~1.0）在两端传输**，电视端按自身 `wm size` 换算成绝对像素。原因：目标电视是 4K（3840×2160），模拟器/其他设备可能是 1080p，传绝对像素会点偏。
- **截图与注入依赖无障碍服务**：`takeScreenshot` 需 Android 11（API 30）+ `canTakeScreenshot`；`dispatchGesture` 需 `canPerformGestures`。无障碍一次启用后重启仍有效，这是「无人值守」的基础。不要改用 MediaProjection（每次重启需重新授权，见 ADR-0003）。
- **无 root 时无法给第三方 App 注入方向键 KeyEvent**，遥控采用「看画面点坐标」范式。
- **电源的真关机/开机做不到**，只能熄屏/待机。
- **目标设备**：TCL 75V68M pro（Android 11 / API 30），另有海信电视；真机尚未验证。无障碍/自启/后台存活在国产 ROM 上可能受限 —— [docs/mvp-verification-checklist.md](docs/mvp-verification-checklist.md) 的「五连验证」是落地硬前提。
- 网络：两端出站连到自建 NAS 中继（WSS），**不做 P2P**（见 ADR-0002）。当前骨架不含网络层。

## 工作偏好

- **优先复用开源**，没有合适方案再自行实现（用户明确要求）。
- 自用工具，倾向 KISS、少依赖、自托管。

## 参考文档

- [CONTEXT.md](CONTEXT.md) — 领域词汇表（帮助端 / 被协助端 / 配对 / 会话 / 快照 / 遥控动作 / 撮合 / 中继）
- [docs/adr/](docs/adr/) — 架构决策记录
- [docs/mvp-verification-checklist.md](docs/mvp-verification-checklist.md) — 真机验证清单
