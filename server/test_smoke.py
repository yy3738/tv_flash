"""服务端冒烟测试：用临时库验证登录与设备接口。

在 server/ 目录运行：
    .venv\\Scripts\\python.exe test_smoke.py
"""

import os
import tempfile

os.environ["TVFLASH_DATA"] = tempfile.mkdtemp(prefix="tvflash_test_")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def main():
    with TestClient(app) as client:
        r = client.get("/api/devices")
        assert r.status_code == 401, r.text

        r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, r.text

        r = client.get("/api/devices")
        assert r.status_code == 200 and r.json()["devices"] == [], r.text

        r = client.post("/api/devices", json={"name": "客厅电视"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["token"] and data["deviceId"], r.text

        r = client.get("/api/devices")
        assert len(r.json()["devices"]) == 1, r.text

    print("SMOKE OK, token:", data["token"])


if __name__ == "__main__":
    main()
