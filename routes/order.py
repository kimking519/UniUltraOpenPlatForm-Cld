"""
订单管理路由模块
"""
import urllib.parse
from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse

from Sills.base import get_db_connection, get_paginated_list
from Sills.db_cli import get_cli_list
from Sills.db_order import (
    get_order_list, add_order, update_order, update_order_status,
    delete_order, batch_import_order, batch_delete_order
)
from routes.auth import login_required, templates

router = APIRouter(prefix="/order", tags=["order"])


@router.get("", response_class=HTMLResponse)
async def order_page(
    request: Request, current_user: dict = Depends(login_required),
    page: int = 1, page_size: int = 20, search: str = "",
    cli_id: str = "", start_date: str = "", end_date: str = "",
    is_finished: str = "", is_transferred: str = ""
):
    """订单列表页面"""
    results, total = get_order_list(
        page=page, page_size=page_size, search_kw=search,
        cli_id=cli_id, start_date=start_date, end_date=end_date,
        is_finished=is_finished, is_transferred=is_transferred
    )
    total_pages = (total + page_size - 1) // page_size
    cli_list, _ = get_cli_list(page=1, page_size=1000)
    cli_list = sorted(cli_list, key=lambda x: x.get('cli_name', ''))
    vendor_data = get_paginated_list('uni_vendor', page=1, page_size=1000)
    vendor_list = vendor_data['items']

    return templates.TemplateResponse("order.html", {
        "request": request,
        "active_page": "order",
        "current_user": current_user,
        "items": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "search": search,
        "cli_id": cli_id,
        "start_date": start_date,
        "end_date": end_date,
        "cli_list": cli_list,
        "vendor_list": vendor_list,
        "is_finished": is_finished,
        "is_transferred": request.query_params.get("is_transferred", "")
    })


@router.post("/add")
async def order_add_route(
    cli_id: str = Form(...), offer_id: str = Form(None),
    order_id: str = Form(None), order_date: str = Form(None),
    inquiry_mpn: str = Form(None), inquiry_brand: str = Form(None),
    is_finished: int = Form(0), is_paid: int = Form(0),
    paid_amount: float = Form(0.0), remark: str = Form(""),
    current_user: dict = Depends(login_required)
):
    """添加订单"""
    data = {
        "cli_id": cli_id, "offer_id": offer_id, "order_id": order_id, "order_date": order_date,
        "inquiry_mpn": inquiry_mpn, "inquiry_brand": inquiry_brand,
        "is_finished": is_finished, "is_paid": is_paid,
        "paid_amount": paid_amount, "remark": remark
    }
    ok, msg = add_order(data)
    return RedirectResponse(url=f"/order?msg={urllib.parse.quote(msg)}&success={1 if ok else 0}", status_code=303)


@router.post("/import")
async def order_import_text(
    batch_text: str = Form(None), csv_file: UploadFile = File(None),
    cli_id: str = Form(...), current_user: dict = Depends(login_required)
):
    """批量导入订单"""
    if batch_text:
        text = batch_text
    elif csv_file:
        content = await csv_file.read()
        try:
            text = content.decode('utf-8-sig').strip()
        except UnicodeDecodeError:
            text = content.decode('gbk', errors='replace').strip()
    else:
        return RedirectResponse(url="/order?msg=未提供导入内容&success=0", status_code=303)

    success_count, errors = batch_import_order(text, cli_id)
    err_msg = ""
    if errors:
        err_msg = "&msg=" + urllib.parse.quote(errors[0])
    return RedirectResponse(url=f"/order?import_success={success_count}&errors={len(errors)}{err_msg}", status_code=303)


# API 端点
api_router = APIRouter(tags=["order-api"])


@api_router.post("/api/order/update_status")
async def api_order_update_status(
    order_id: str = Form(...), field: str = Form(...),
    value: int = Form(...), current_user: dict = Depends(login_required)
):
    """更新订单状态"""
    ok, msg = update_order_status(order_id, field, value)
    return {"success": ok, "message": msg}


@api_router.post("/api/order/update")
async def api_order_update(
    order_id: str = Form(...), field: str = Form(...),
    value: str = Form(...), current_user: dict = Depends(login_required)
):
    """更新订单API"""
    if field in ['paid_amount']:
        try:
            value = float(value)
        except:
            return {"success": False, "message": "必须是数字"}

    allowed_fields = ['order_no', 'order_date', 'cli_id', 'offer_id', 'inquiry_mpn', 'inquiry_brand', 'price_rmb', 'price_kwr', 'price_usd', 'cost_price_rmb', 'is_finished', 'is_paid', 'paid_amount', 'return_status', 'remark', 'is_transferred']
    if field not in allowed_fields:
        return {"success": False, "message": f"非法字段: {field}"}

    ok, msg = update_order(order_id, {field: value})
    return {"success": ok, "message": msg}


@api_router.post("/api/order/delete")
async def api_order_delete(order_id: str = Form(...), current_user: dict = Depends(login_required)):
    """删除订单API"""
    if current_user['rule'] != '3':
        return {"success": False, "message": "无权限"}
    ok, msg = delete_order(order_id)
    return {"success": ok, "message": msg}


@api_router.post("/api/order/batch_delete")
async def api_order_batch_delete(request: Request, current_user: dict = Depends(login_required)):
    """批量删除订单"""
    if current_user['rule'] != '3':
        return {"success": False, "message": "仅管理员可删除"}
    data = await request.json()
    ids = data.get("ids", [])
    ok, msg = batch_delete_order(ids)
    return {"success": ok, "message": msg}