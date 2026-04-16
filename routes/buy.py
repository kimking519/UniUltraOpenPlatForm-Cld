"""
采购管理路由模块
"""
import urllib.parse
from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse

from Sills.base import get_db_connection
from Sills.db_buy import (
    get_buy_list, add_buy, update_buy, update_buy_node,
    delete_buy, batch_import_buy, batch_delete_buy
)
from routes.auth import login_required, templates

router = APIRouter(prefix="/buy", tags=["buy"])


@router.get("", response_class=HTMLResponse)
async def buy_page(
    request: Request, current_user: dict = Depends(login_required),
    page: int = 1, page_size: int = 20, search: str = "",
    order_id: str = "", start_date: str = "", end_date: str = "",
    cli_id: str = "", is_shipped: str = ""
):
    """采购列表页面"""
    results, total = get_buy_list(
        page=page, page_size=page_size, search_kw=search,
        order_id=order_id, start_date=start_date, end_date=end_date,
        cli_id=cli_id, is_shipped=is_shipped
    )
    total_pages = (total + page_size - 1) // page_size
    with get_db_connection() as conn:
        vendors = conn.execute("SELECT vendor_id, vendor_name, address FROM uni_vendor").fetchall()
        orders = conn.execute("SELECT order_id, order_no FROM uni_order").fetchall()
        clis = conn.execute("SELECT cli_id, cli_name FROM uni_cli ORDER BY cli_name").fetchall()
        vendor_addresses = {str(v['vendor_id']): (v['address'] or "") for v in vendors}

    return templates.TemplateResponse("buy.html", {
        "request": request,
        "active_page": "buy",
        "current_user": current_user,
        "items": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "search": search,
        "order_id": order_id,
        "start_date": start_date,
        "end_date": end_date,
        "cli_id": cli_id,
        "vendor_list": vendors,
        "order_list": orders,
        "cli_list": clis,
        "is_shipped": is_shipped,
        "vendor_addresses": vendor_addresses
    })


@router.post("/import")
async def buy_import_text(
    batch_text: str = Form(None), csv_file: UploadFile = File(None),
    current_user: dict = Depends(login_required)
):
    """批量导入采购"""
    if batch_text:
        text = batch_text
    elif csv_file:
        content = await csv_file.read()
        try:
            text = content.decode('utf-8-sig').strip()
        except UnicodeDecodeError:
            text = content.decode('gbk', errors='replace').strip()
    else:
        return RedirectResponse(url="/buy?import_success=0&errors=1&msg=未提供导入内容", status_code=303)

    success_count, errors = batch_import_buy(text)
    err_msg = ""
    if errors:
        err_msg = "&msg=" + urllib.parse.quote(errors[0])
    return RedirectResponse(url=f"/buy?import_success={success_count}&errors={len(errors)}{err_msg}", status_code=303)


@router.post("/add")
async def buy_add_route(
    order_id: str = Form(...), vendor_id: str = Form(...),
    buy_mpn: str = Form(...), buy_brand: str = Form(""),
    buy_price_rmb: float = Form(...), buy_qty: int = Form(...),
    sales_price_rmb: float = Form(0.0), remark: str = Form(""),
    current_user: dict = Depends(login_required)
):
    """添加采购"""
    data = {
        "order_id": order_id, "vendor_id": vendor_id,
        "buy_mpn": buy_mpn, "buy_brand": buy_brand,
        "buy_price_rmb": buy_price_rmb, "buy_qty": buy_qty,
        "sales_price_rmb": sales_price_rmb, "remark": remark
    }
    ok, msg = add_buy(data)
    msg_param = urllib.parse.quote(msg)
    success = 1 if ok else 0
    return RedirectResponse(url=f"/buy?msg={msg_param}&success={success}", status_code=303)


# API 端点
api_router = APIRouter(tags=["buy-api"])


@api_router.post("/api/buy/update_node")
async def api_buy_update_node(
    buy_id: str = Form(...), field: str = Form(...),
    value: int = Form(...), current_user: dict = Depends(login_required)
):
    """更新采购节点状态"""
    ok, msg = update_buy_node(buy_id, field, value)
    return {"success": ok, "message": msg}


@api_router.post("/api/buy/update")
async def api_buy_update(
    buy_id: str = Form(...), field: str = Form(...),
    value: str = Form(...), current_user: dict = Depends(login_required)
):
    """更新采购API"""
    if current_user['rule'] not in ['3', '0']:
        return {"success": False, "message": "无权限"}
    allowed_fields = ['order_id', 'vendor_id', 'buy_mpn', 'buy_brand', 'buy_price_rmb', 'buy_qty', 'sales_price_rmb', 'remark', 'price_kwr', 'price_usd']
    if field not in allowed_fields:
        return {"success": False, "message": f"非法字段: {field}"}
    success, msg = update_buy(buy_id, {field: value})
    return {"success": success, "message": msg}


@api_router.post("/api/buy/delete")
async def api_buy_delete(buy_id: str = Form(...), current_user: dict = Depends(login_required)):
    """删除采购API"""
    if current_user['rule'] != '3':
        return {"success": False, "message": "仅管理员可删除"}
    ok, msg = delete_buy(buy_id)
    return {"success": ok, "message": msg}


@api_router.post("/api/buy/batch_delete")
async def api_buy_batch_delete(request: Request, current_user: dict = Depends(login_required)):
    """批量删除采购"""
    if current_user['rule'] != '3':
        return {"success": False, "message": "仅管理员可删除"}
    data = await request.json()
    ids = data.get("ids", [])
    ok, msg = batch_delete_buy(ids)
    return {"success": ok, "message": msg}