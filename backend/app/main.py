from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, clients, cases, documents, ingestion, portal_assist, classify, search, analytics, vouchers, settings, spreadsheet, raw_parser, research, document_rules
from app.database import engine, Base
from app.db_migration import sync_migrate_sqlite_schema
import app.models  # ensure models are registered with Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(sync_migrate_sqlite_schema)
    yield

app = FastAPI(title="Filestavk API", version="0.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(clients.router, prefix="/clients", tags=["clients"])
app.include_router(cases.router, prefix="/cases", tags=["cases"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(document_rules.router, prefix="/document-rules", tags=["document_rules"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
app.include_router(portal_assist.router, prefix="/portal", tags=["portal_assist"])
app.include_router(raw_parser.router, prefix="/portal", tags=["portal_raw_parser"])
app.include_router(spreadsheet.router, prefix="/spreadsheet", tags=["spreadsheet"])
app.include_router(research.router, prefix="/research", tags=["research"])
app.include_router(classify.router, prefix="/classify", tags=["classify"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(vouchers.router, prefix="/vouchers", tags=["vouchers"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])


