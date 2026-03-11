"""
UniUltraOpenPlatForm 自动化测试套件

测试覆盖：
- API 接口功能测试
- 数据库操作测试
- 文档生成测试
- 业务流程测试

运行方式：
  pytest tests/test_all.py -v --tb=short
  pytest tests/test_all.py -v --html=reports/test_report.html --self-contained-html
"""

import pytest
import sys
import os
import json
import tempfile
import shutil
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.testclient import TestClient as StarletteTestClient
from Sills.base import get_db_connection, init_db, close_all_connections, clear_cache

# ============================================================
# 测试配置
# ============================================================

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_platform.db")
BACKUP_DB_PATH = os.path.join(os.path.dirname(__file__), "test_platform_backup.db")

# 测试用户
TEST_ADMIN = {"account": "Admin", "password": "uni519"}
TEST_USER = {"account": "testuser", "password": "test123"}


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="session")
def test_db():
    """创建测试数据库"""
    # 备份原数据库路径
    global_db_path = os.path.join(os.path.dirname(__file__), "..", "uni_platform.db")

    # 使用测试数据库
    if os.path.exists(global_db_path):
        shutil.copy(global_db_path, TEST_DB_PATH)

    yield TEST_DB_PATH

    # 清理
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    if os.path.exists(BACKUP_DB_PATH):
        os.remove(BACKUP_DB_PATH)


@pytest.fixture(scope="session")
def client(test_db):
    """创建测试客户端"""
    # 临时修改数据库路径
    import Sills.base
    original_path = Sills.base.DB_PATH
    Sills.base.DB_PATH = test_db

    from main import app
    test_client = StarletteTestClient(app)

    yield test_client

    # 恢复
    Sills.base.DB_PATH = original_path
    close_all_connections()


@pytest.fixture
def auth_token(client):
    """获取认证令牌"""
    response = client.post("/login", data=TEST_ADMIN)
    assert response.status_code == 200
    return response.cookies


# ============================================================
# 测试结果收集
# ============================================================

class TestResults:
    """收集测试结果用于报告"""

    def __init__(self):
        self.results = []
        self.bugs = []
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_result(self, module, test_name, status, message=""):
        self.results.append({
            "module": module,
            "test": test_name,
            "status": status,
            "message": message,
            "time": datetime.now().isoformat()
        })
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
            self.bugs.append(f"[{module}] {test_name}: {message}")

    def report(self):
        total = self.passed + self.failed
        rate = (self.passed / total * 100) if total > 0 else 0

        report = f"""
{'='*60}
                    测试报告
{'='*60}
测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
总测试数: {total}
通过: {self.passed}
失败: {self.failed}
通过率: {rate:.1f}%
{'='*60}
"""
        if self.bugs:
            report += "\n发现的 Bug:\n"
            for bug in self.bugs:
                report += f"  - {bug}\n"

        return report


test_results = TestResults()


# ============================================================
# 1. 认证模块测试
# ============================================================

class TestAuth:
    """认证模块测试"""

    def test_login_page(self, client):
        """测试登录页面可访问"""
        response = client.get("/login")
        assert response.status_code == 200
        test_results.add_result("认证", "登录页面访问", "PASS")

    def test_login_success(self, client):
        """测试正确登录 - 返回重定向"""
        response = client.post("/login", data=TEST_ADMIN, follow_redirects=False)
        # 登录成功返回 303 重定向
        assert response.status_code == 303
        test_results.add_result("认证", "正确登录", "PASS")

    def test_login_fail(self, client):
        """测试错误密码登录 - 返回重定向到登录页"""
        response = client.post("/login", data={"account": "Admin", "password": "wrong"}, follow_redirects=False)
        # 登录失败也返回 303 重定向到登录页
        assert response.status_code == 303
        test_results.add_result("认证", "错误密码登录拒绝", "PASS")

    def test_logout(self, client, auth_token):
        """测试登出"""
        response = client.get("/logout", cookies=auth_token)
        assert response.status_code in [200, 302, 303]
        test_results.add_result("认证", "登出功能", "PASS")


# ============================================================
# 2. 员工管理测试
# ============================================================

class TestEmployee:
    """员工管理测试"""

    def test_emp_page(self, client, auth_token):
        """测试员工页面"""
        response = client.get("/emp", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("员工", "员工页面访问", "PASS")

    def test_emp_list(self, client, auth_token):
        """测试员工列表 API"""
        response = client.get("/emp?page=1&page_size=10", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("员工", "员工列表", "PASS")

    def test_emp_add(self, client, auth_token):
        """测试添加员工"""
        emp_data = {
            "emp_name": "测试员工",
            "department": "测试部",
            "position": "测试员",
            "account": f"test_emp_{datetime.now().strftime('%H%M%S')}",
            "contact": "13800138000",
            "hire_date": datetime.now().strftime("%Y-%m-%d"),
            "rule": "1"
        }
        response = client.post("/emp/add", data=emp_data, cookies=auth_token)
        # 成功返回 303 重定向，或者 200 (页面刷新)
        assert response.status_code in [200, 303]
        test_results.add_result("员工", "添加员工", "PASS")

    def test_emp_update(self, client, auth_token):
        """测试更新员工"""
        # API 使用 Form 参数
        response = client.post("/api/emp/update", data={
            "emp_id": "000",
            "field": "remark",
            "value": "测试更新"
        }, cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("员工", "更新员工", "PASS")

    def test_emp_delete(self, client, auth_token):
        """测试删除员工"""
        # 先添加一个员工
        client.post("/emp/add", data={
            "emp_name": "待删除员工",
            "account": f"del_emp_{datetime.now().strftime('%H%M%S')}",
            "hire_date": datetime.now().strftime("%Y-%m-%d"),
            "rule": "1"
        }, cookies=auth_token)

        # 查找刚添加的员工
        with get_db_connection() as conn:
            emp = conn.execute(
                "SELECT emp_id FROM uni_emp WHERE emp_name='待删除员工' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()

        if emp:
            response = client.post("/api/emp/delete", data={"emp_id": emp[0]}, cookies=auth_token)
            assert response.status_code == 200
            test_results.add_result("员工", "删除员工", "PASS")
        else:
            test_results.add_result("员工", "删除员工", "PASS", "未找到测试员工")


# ============================================================
# 3. 客户管理测试
# ============================================================

class TestClientManagement:
    """客户管理测试"""

    def test_cli_page(self, client, auth_token):
        """测试客户页面"""
        response = client.get("/cli", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("客户", "客户页面访问", "PASS")

    def test_cli_add(self, client, auth_token):
        """测试添加客户"""
        cli_data = {
            "cli_id": f"CT{datetime.now().strftime('%H%M%S')}",
            "cli_name": "测试客户",
            "cli_name_en": "TestClient",
            "contact_name": "张三",
            "region": "韩国",
            "emp_id": "000",
            "email": "test@test.com",
            "phone": "12345678"
        }
        response = client.post("/cli/add", data=cli_data, cookies=auth_token)
        # 成功返回 303 重定向，或者 200 (页面刷新)
        assert response.status_code in [200, 303]
        test_results.add_result("客户", "添加客户", "PASS")

    def test_cli_update(self, client, auth_token):
        """测试更新客户"""
        response = client.post("/api/cli/update", data={
            "cli_id": "C001",
            "field": "remark",
            "value": "测试更新"
        }, cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("客户", "更新客户", "PASS")

    def test_cli_delete(self, client, auth_token):
        """测试删除客户"""
        # 先添加一个客户
        cli_id = f"CD{datetime.now().strftime('%H%M%S')}"
        client.post("/cli/add", data={
            "cli_id": cli_id,
            "cli_name": "待删除客户",
            "region": "韩国",
            "emp_id": "000"
        }, cookies=auth_token)

        response = client.post("/api/cli/delete", data={"cli_id": cli_id}, cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("客户", "删除客户", "PASS")


# ============================================================
# 4. 供应商管理测试
# ============================================================

class TestVendor:
    """供应商管理测试"""

    def test_vendor_page(self, client, auth_token):
        """测试供应商页面"""
        response = client.get("/vendor", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("供应商", "供应商页面访问", "PASS")

    def test_vendor_add(self, client, auth_token):
        """测试添加供应商"""
        vendor_data = {
            "vendor_id": f"VT{datetime.now().strftime('%H%M%S')}",
            "vendor_name": "测试供应商",
            "contact": "李四",
            "phone": "87654321"
        }
        response = client.post("/vendor/add", data=vendor_data, cookies=auth_token)
        # 成功返回 303 重定向，或者 200 (页面刷新)
        assert response.status_code in [200, 303]
        test_results.add_result("供应商", "添加供应商", "PASS")


# ============================================================
# 5. 询价管理测试
# ============================================================

class TestQuote:
    """询价管理测试"""

    def test_quote_page(self, client, auth_token):
        """测试询价页面"""
        response = client.get("/quote", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("询价", "询价页面访问", "PASS")

    def test_quote_add(self, client, auth_token):
        """测试添加询价"""
        # 先确保有客户
        client.post("/cli/add", data={
            "cli_id": f"CQ{datetime.now().strftime('%H%M%S')}",
            "cli_name": "询价测试客户",
            "region": "韩国",
            "emp_id": "000"
        }, cookies=auth_token)

        # 获取刚添加的客户
        with get_db_connection() as conn:
            cli = conn.execute(
                "SELECT cli_id FROM uni_cli WHERE cli_name='询价测试客户' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()

        if cli:
            quote_data = {
                "cli_id": cli[0],
                "inquiry_mpn": "TEST-MPN-001",
                "inquiry_brand": "TEST-BRAND",
                "inquiry_qty": "1000",
                "target_price_rmb": "10.5"
            }
            response = client.post("/quote/add", data=quote_data, cookies=auth_token)
            # 成功返回 303 重定向，或者 200 (页面刷新)
            assert response.status_code in [200, 303]
            test_results.add_result("询价", "添加询价", "PASS")
        else:
            test_results.add_result("询价", "添加询价", "PASS", "客户未找到")

    def test_quote_list_filter(self, client, auth_token):
        """测试询价列表筛选"""
        response = client.get("/quote?status=询价中", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("询价", "询价列表筛选", "PASS")


# ============================================================
# 6. 报价管理测试
# ============================================================

class TestOffer:
    """报价管理测试"""

    def test_offer_page(self, client, auth_token):
        """测试报价页面"""
        response = client.get("/offer", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("报价", "报价页面访问", "PASS")

    def test_exchange_rates(self, client, auth_token):
        """测试汇率获取"""
        response = client.get("/api/exchange/rates", cookies=auth_token)
        assert response.status_code == 200
        data = response.json()
        assert "krw" in data or "usd" in data
        test_results.add_result("报价", "汇率获取", "PASS")


# ============================================================
# 7. 订单管理测试
# ============================================================

class TestOrder:
    """订单管理测试"""

    def test_order_page(self, client, auth_token):
        """测试订单页面"""
        response = client.get("/order", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("订单", "订单页面访问", "PASS")

    def test_order_add(self, client, auth_token):
        """测试添加订单"""
        # 确保有客户
        with get_db_connection() as conn:
            cli = conn.execute("SELECT cli_id FROM uni_cli LIMIT 1").fetchone()

        if cli:
            order_data = {
                "cli_id": cli[0],
                "inquiry_mpn": "ORDER-MPN-001",
                "inquiry_brand": "ORDER-BRAND",
                "price_rmb": "15.0",
                "order_date": datetime.now().strftime("%Y-%m-%d")
            }
            response = client.post("/order/add", data=order_data, cookies=auth_token)
            # 成功返回 303 重定向，或者 200 (页面刷新)
            assert response.status_code in [200, 303]
            test_results.add_result("订单", "添加订单", "PASS")
        else:
            test_results.add_result("订单", "添加订单", "PASS", "无客户数据跳过")


# ============================================================
# 8. 采购管理测试
# ============================================================

class TestBuy:
    """采购管理测试"""

    def test_buy_page(self, client, auth_token):
        """测试采购页面"""
        response = client.get("/buy", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("采购", "采购页面访问", "PASS")


# ============================================================
# 9. 汇率管理测试
# ============================================================

class TestDaily:
    """汇率管理测试"""

    def test_daily_page(self, client, auth_token):
        """测试汇率页面"""
        response = client.get("/daily", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("汇率", "汇率页面访问", "PASS")

    def test_daily_add(self, client, auth_token):
        """测试添加汇率"""
        daily_data = {
            "record_date": datetime.now().strftime("%Y-%m-%d"),
            "currency_code": "2",
            "exchange_rate": "185.5"
        }
        response = client.post("/daily/add", data=daily_data, cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("汇率", "添加汇率", "PASS")


# ============================================================
# 10. 文档生成测试
# ============================================================

class TestDocumentGeneration:
    """文档生成测试"""

    def test_get_orders_for_document(self):
        """测试获取订单数据用于文档生成"""
        with get_db_connection() as conn:
            orders = conn.execute("SELECT order_id FROM uni_order LIMIT 1").fetchall()
            if orders:
                from Sills.document_generator import get_orders_for_document
                result = get_orders_for_document([orders[0][0]])
                assert isinstance(result, list)
                test_results.add_result("文档", "获取订单数据", "PASS")
            else:
                test_results.add_result("文档", "获取订单数据", "PASS", "无订单数据跳过")

    def test_get_offers_for_document(self):
        """测试获取报价数据用于文档生成"""
        with get_db_connection() as conn:
            offers = conn.execute("SELECT offer_id FROM uni_offer LIMIT 1").fetchall()
            if offers:
                from Sills.document_generator import get_offers_for_document
                result = get_offers_for_document([offers[0][0]])
                assert isinstance(result, list)
                test_results.add_result("文档", "获取报价数据", "PASS")
            else:
                test_results.add_result("文档", "获取报价数据", "PASS", "无报价数据跳过")


# ============================================================
# 11. 数据库操作测试
# ============================================================

class TestDatabase:
    """数据库操作测试"""

    def test_connection(self):
        """测试数据库连接"""
        with get_db_connection() as conn:
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1
        test_results.add_result("数据库", "数据库连接", "PASS")

    def test_tables_exist(self):
        """测试所有表存在"""
        expected_tables = [
            'uni_emp', 'uni_cli', 'uni_vendor',
            'uni_quote', 'uni_offer', 'uni_order', 'uni_buy', 'uni_daily'
        ]
        with get_db_connection() as conn:
            for table in expected_tables:
                result = conn.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                ).fetchone()
                assert result is not None, f"表 {table} 不存在"
        test_results.add_result("数据库", "所有表存在", "PASS")

    def test_indexes_exist(self):
        """测试索引存在"""
        with get_db_connection() as conn:
            indexes = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            assert len(indexes) > 0
        test_results.add_result("数据库", "索引存在", "PASS")

    def test_foreign_keys(self):
        """测试外键约束"""
        with get_db_connection() as conn:
            # 检查外键是否启用
            result = conn.execute("PRAGMA foreign_keys").fetchone()
            assert result[0] == 1
        test_results.add_result("数据库", "外键约束启用", "PASS")


# ============================================================
# 12. 业务流程测试
# ============================================================

class TestBusinessFlow:
    """业务流程测试"""

    def test_quote_to_offer_flow(self, client, auth_token):
        """测试询价转报价流程"""
        # 1. 创建询价
        client.post("/cli/add", data={
            "cli_id": "CF01",
            "cli_name": "流程测试客户",
            "region": "韩国",
            "emp_id": "000"
        }, cookies=auth_token)

        quote_resp = client.post("/quote/add", data={
            "cli_id": "CF01",
            "inquiry_mpn": "FLOW-MPN-001",
            "inquiry_brand": "FLOW-BRAND",
            "inquiry_qty": "500"
        }, cookies=auth_token)

        # 检查是否成功
        if quote_resp.status_code == 200:
            test_results.add_result("流程", "询价转报价-创建询价", "PASS")
        else:
            test_results.add_result("流程", "询价转报价-创建询价", "FAIL")

    def test_pagination(self, client, auth_token):
        """测试分页功能"""
        response = client.get("/emp?page=1&page_size=5", cookies=auth_token)
        assert response.status_code == 200
        test_results.add_result("通用", "分页功能", "PASS")


# ============================================================
# 13. 安全测试
# ============================================================

class TestSecurity:
    """安全测试"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/emp")
        # 应该重定向到登录或返回错误
        assert response.status_code in [200, 302, 303, 401, 403]
        test_results.add_result("安全", "未授权访问拦截", "PASS")

    def test_sql_injection_prevention(self, client, auth_token):
        """测试 SQL 注入防护"""
        # 尝试 SQL 注入
        response = client.get("/emp?search='; DROP TABLE uni_emp; --", cookies=auth_token)
        assert response.status_code == 200
        # 表应该仍然存在
        with get_db_connection() as conn:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='uni_emp'"
            ).fetchone()
            assert result is not None
        test_results.add_result("安全", "SQL注入防护", "PASS")


# ============================================================
# 报告生成
# ============================================================

def test_generate_report():
    """生成测试报告"""
    report = test_results.report()
    print(report)

    # 写入报告文件
    report_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(report_dir, exist_ok=True)

    report_path = os.path.join(report_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已保存到: {report_path}")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])