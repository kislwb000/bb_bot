from .events import router as events_router
from .export_excel import router as export_excel_router
from .report import router as report_router
from .teams import router as teams_router

routers = [events_router, teams_router, report_router, export_excel_router]
