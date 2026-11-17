"""命令行创建一个电视设备并打印令牌。

用法（在 server/ 目录下）：
    python -m app.make_device "客厅电视"
"""

import sys
import time
import uuid

from .auth import hash_token, new_token
from .db import db, init_db


def main():
    init_db()
    name = sys.argv[1] if len(sys.argv) > 1 else "TV"
    with db() as conn:
        account = conn.execute(
            "SELECT id FROM sys_account WHERE deleted=1 LIMIT 1"
        ).fetchone()
        if account is None:
            print("未找到账号，请先启动服务一次以初始化 admin 账号。")
            return
        token = new_token()
        device_id = uuid.uuid4().hex
        now = int(time.time() * 1000)
        conn.execute(
            "INSERT INTO biz_device "
            "(id, account_id, name, token_hash, online, version, deleted, create_time, update_time) "
            "VALUES (?, ?, ?, ?, 0, 0, 1, ?, ?)",
            (device_id, account["id"], name, hash_token(token), now, now),
        )
    print("deviceId:", device_id)
    print("token   :", token)


if __name__ == "__main__":
    main()
