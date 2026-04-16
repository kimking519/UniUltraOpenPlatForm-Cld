"""
路由模块包
"""
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

# 导入所有路由模块
from routes.auth import router as auth_router, api_router as auth_api_router, init_templates
from routes.emp import router as emp_router, api_router as emp_api_router
from routes.vendor import router as vendor_router, api_router as vendor_api_router
from routes.cli import router as cli_router, api_router as cli_api_router
from routes.quote import router as quote_router, api_router as quote_api_router
from routes.offer import router as offer_router, api_router as offer_api_router
from routes.order import router as order_router, api_router as order_api_router
from routes.buy import router as buy_router, api_router as buy_api_router
from routes.daily import router as daily_router, api_router as daily_api_router


def register_routes(app: FastAPI, templates: Jinja2Templates):
    """注册所有路由到FastAPI应用"""
    # 初始化模板对象
    init_templates(templates)

    # 注册页面路由
    app.include_router(auth_router)
    app.include_router(emp_router)
    app.include_router(vendor_router)
    app.include_router(cli_router)
    app.include_router(quote_router)
    app.include_router(offer_router)
    app.include_router(order_router)
    app.include_router(buy_router)
    app.include_router(daily_router)

    # 注册API路由（不带前缀）
    app.include_router(auth_api_router)
    app.include_router(emp_api_router)
    app.include_router(vendor_api_router)
    app.include_router(cli_api_router)
    app.include_router(quote_api_router)
    app.include_router(offer_api_router)
    app.include_router(order_api_router)
    app.include_router(buy_api_router)
    app.include_router(daily_api_router)