"""
汇率管理路由模块
"""
from datetime import datetime
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

from Sills.db_daily import get_daily_list, add_daily, update_daily
from routes.auth import login_required, templates

router = APIRouter(prefix="/daily", tags=["daily"])


@router.get("", response_class=HTMLResponse)
async def daily_page(request: Request, page: int = 1, current_user: dict = Depends(login_required)):
    """汇率列表页面"""
    items, total = get_daily_list(page=page)
    return templates.TemplateResponse("daily.html", {
        "request": request,
        "active_page": "daily",
        "current_user": current_user,
        "items": items,
        "total": total,
        "page": page
    })


@router.post("/add")
async def daily_add(currency_code: int = Form(...), exchange_rate: float = Form(...), current_user: dict = Depends(login_required)):
    """添加汇率记录"""
    record_date = datetime.now().strftime('%Y-%m-%d')
    success, msg = add_daily(record_date, currency_code, exchange_rate)
    return RedirectResponse(url="/daily", status_code=303)


# API 端点
api_router = APIRouter(tags=["daily-api"])


@api_router.post("/api/daily/update")
async def daily_update_api(id: int = Form(...), exchange_rate: float = Form(...), current_user: dict = Depends(login_required)):
    """更新汇率API"""
    success, msg = update_daily(id, exchange_rate)
    return {"success": success, "message": msg}