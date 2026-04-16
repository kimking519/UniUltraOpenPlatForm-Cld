"""
供应商管理路由模块
"""
from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse

from Sills.base import get_paginated_list
from Sills.db_vendor import add_vendor, batch_import_vendor_text, update_vendor, delete_vendor
from routes.auth import login_required, templates

router = APIRouter(prefix="/vendor", tags=["vendor"])


@router.get("", response_class=HTMLResponse)
async def vendor_page(request: Request, page: int = 1, search: str = "", current_user: dict = Depends(login_required)):
    """供应商列表页面"""
    search_kwargs = {"vendor_name": search} if search else None
    result = get_paginated_list("uni_vendor", page=page, search_kwargs=search_kwargs)
    return templates.TemplateResponse("vendor.html", {
        "request": request,
        "active_page": "vendor",
        "current_user": current_user,
        "items": result["items"],
        "total_pages": result["total_pages"],
        "page": page,
        "search": search
    })


@router.post("/add")
async def vendor_add(
    vendor_name: str = Form(...), address: str = Form(""), qq: str = Form(""),
    wechat: str = Form(""), email: str = Form(""), remark: str = Form(""),
    current_user: dict = Depends(login_required)
):
    """添加供应商"""
    data = {
        "vendor_name": vendor_name, "address": address, "qq": qq,
        "wechat": wechat, "email": email, "remark": remark
    }
    add_vendor(data)
    return RedirectResponse(url="/vendor", status_code=303)


@router.post("/import")
async def vendor_import(import_text: str = Form(...), current_user: dict = Depends(login_required)):
    """批量导入供应商（文本）"""
    batch_import_vendor_text(import_text)
    return RedirectResponse(url="/vendor", status_code=303)


@router.post("/import/csv")
async def vendor_import_csv(csv_file: UploadFile = File(...), current_user: dict = Depends(login_required)):
    """批量导入供应商（CSV）"""
    content = await csv_file.read()
    try:
        text = content.decode('utf-8-sig').strip()
    except UnicodeDecodeError:
        text = content.decode('gbk', errors='replace').strip()

    if '\n' in text:
        text = text.split('\n', 1)[1]  # skip header
    batch_import_vendor_text(text)
    return RedirectResponse(url="/vendor", status_code=303)


# API 端点
api_router = APIRouter(tags=["vendor-api"])


@api_router.post("/api/vendor/update")
async def vendor_update_api(vendor_id: str = Form(...), field: str = Form(...), value: str = Form(...), current_user: dict = Depends(login_required)):
    """更新供应商API"""
    allowed_fields = ['vendor_name', 'address', 'qq', 'wechat', 'email', 'remark']
    if field not in allowed_fields:
        return {"success": False, "message": "非法字段"}

    success, msg = update_vendor(vendor_id, {field: value})
    return {"success": success, "message": msg}


@api_router.post("/api/vendor/delete")
async def vendor_delete_api(vendor_id: str = Form(...), current_user: dict = Depends(login_required)):
    """删除供应商API"""
    success, msg = delete_vendor(vendor_id)
    return {"success": success, "message": msg}