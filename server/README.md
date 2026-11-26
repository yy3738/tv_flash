# TV Flash 服务端（FastAPI）

## 运行

```bash
cd server
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 启动（默认 0.0.0.0:8080）
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

首次启动会自动建库并初始化单账号：默认 `admin / admin123`（用环境变量
`TVFLASH_ADMIN` / `TVFLASH_PASSWORD` / `TVFLASH_SECRET` 覆盖）。

## 创建电视设备令牌

```bash
python -m app.make_device "客厅电视"
```

会打印 `deviceId` 和 `token`；把 `token` 和 NAS 地址填入电视端 App。

## 接口速览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/login` | `{username,password}` → session cookie |
| POST | `/api/logout` | 登出 |
| GET  | `/api/devices` | 设备列表 |
| POST | `/api/devices` | `{name}` → 返回 `token`（仅一次） |
| POST | `/api/devices/{id}/kick` | 断开/拉黑 |
| WS   | `/ws/web` | 浏览器（cookie 鉴权） |
| WS   | `/ws/tv?token=...` | 电视端（令牌鉴权） |

## 测试

```bash
python test_smoke.py      # REST 冒烟（临时库，无需服务运行）
python test_ws.py         # 中继单帧验证（需服务与电视端运行）
python test_refresh.py    # 慢刷 10 帧压测（需服务与电视端运行）
```

## 前端静态资源

Vue 构建产物放到 `server/web_dist/`（或设 `TVFLASH_WEB`），启动后由 `/` 托管。
