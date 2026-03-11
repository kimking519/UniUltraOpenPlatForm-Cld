"""
测试配置文件

提供共享的 fixtures 和配置。
"""

import pytest
import subprocess
import time
import socket
import sys
import os

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def wait_for_server(host, port, timeout=30):
    """等待服务器启动"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def server():
    """启动测试服务器"""
    import threading
    import uvicorn

    # 在后台线程启动服务器
    def run_server():
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8000,
            log_level="error"
        )

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # 等待服务器启动
    if not wait_for_server("127.0.0.1", 8000, timeout=10):
        pytest.fail("服务器启动失败")

    yield

    # 服务器会随线程结束而关闭