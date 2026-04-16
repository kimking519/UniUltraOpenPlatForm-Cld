"""
员工管理路由模块
"""
from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

from Sills.db_emp import get_emp_list, add_employee, batch_import_text, update_employee, delete_employee
from routes.auth import login_required, templates

router = APIRouter(prefix="/emp", tags=["emp"])


@router.get("", response_class=HTMLResponse)
async def emp_page(request: Request, page: int = 1, search: str = "", current_user: dict = Depends(login_required)):
    """员工列表页面"""
    items, total = get_emp_list(page=page, search=search)
    return templates.TemplateResponse("emp.html", {
        "request": request,
        "active_page": "emp",
        "current_user": current_user,
        "items": items,
        "total": total,
        "page": page,
        "search": search
    })


@router.post("/add")
async def emp_add(
    emp_name: str = Form(...), department: str = Form(""), position: str = Form(""),
    contact: str = Form(""), account: str = Form(...), hire_date: str = Form(...),
    rule: str = Form("1"), remark: str = Form(""),
    current_user: dict = Depends(login_required)
):
    """添加员工"""
    if current_user['rule'] not in ['3', '0']:
        return RedirectResponse(url="/emp", status_code=303)

    data = {
        "emp_name": emp_name, "department": department, "position": position,
        "contact": contact, "account": account, "password": "12345",
        "hire_date": hire_date,
        "rule": rule, "remark": remark
    }
    success, msg = add_employee(data)
    return RedirectResponse(url="/emp", status_code=303)


@router.post("/import")
async def emp_import(import_text: str = Form(...), current_user: dict = Depends(login_required)):
    """批量导入员工（文本）"""
    if current_user['rule'] not in ['3', '0']:
        return RedirectResponse(url="/emp", status_code=303)
    success_count, errors = batch_import_text(import_text)
    return RedirectResponse(url=f"/emp?import_success={success_count}&errors={len(errors)}", status_code=303)


@router.post("/import/csv")
async def emp_import_csv(csv_file: UploadFile = File(...), current_user: dict = Depends(login_required)):
    """批量导入员工（CSV）"""
    if current_user['rule'] not in ['3', '0']:
        return RedirectResponse(url="/emp", status_code=303)
    content = await csv_file.read()
    try:
        text = content.decode('utf-8-sig').strip()
    except UnicodeDecodeError:
        text = content.decode('gbk', errors='replace').strip()

    if '\n' in text:
        text = text.split('\n', 1)[1]  # skip header
    success_count, errors = batch_import_text(text)
    return RedirectResponse(url=f"/emp?import_success={success_count}&errors={len(errors)}", status_code=303)


# API 端点（不带 /emp 前缀，因为前端调用的是 /api/emp）
api_router = APIRouter(tags=["emp-api"])


@api_router.post("/api/emp/update")
async def emp_update_api(emp_id: str = Form(...), field: str = Form(...), value: str = Form(...), current_user: dict = Depends(login_required)):
    """更新员工信息API"""
    if current_user['rule'] not in ['3', '0']:
        return {"success": False, "message": "无权限"}
    allowed_fields = ['emp_name', 'account', 'password', 'department', 'position', 'rule', 'contact', 'hire_date', 'remark']
    if field not in allowed_fields:
        return {"success": False, "message": "非法字段"}

    success, msg = update_employee(emp_id, {field: value})
    return {"success": success, "message": msg}


@api_router.post("/api/emp/delete")
async def emp_delete_api(emp_id: str = Form(...), current_user: dict = Depends(login_required)):
    """删除员工API"""
    if current_user['rule'] not in ['3', '0']:
        return {"success": False, "message": "无权限"}
    success, msg = delete_employee(emp_id)
    return {"success": success, "message": msg}