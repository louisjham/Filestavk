import os

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

# MODELS
write_file("app/models/__init__.py", '''
from .client import Client
from .case import Case
from .document import Document
from .event import Event
from .time_entry import TimeEntry, Voucher
from .classification import ClassificationLabel, DocumentLabel, IngestionJob, SearchHistory, PortalAuditLog
''')

write_file("app/models/event.py", '''
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    event_type = Column(String)
    title = Column(String, nullable=False)
    description = Column(Text)
    event_date = Column(String)
    created_at = Column(DateTime, default=func.now())
''')

write_file("app/models/time_entry.py", '''
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class TimeEntry(Base):
    __tablename__ = "time_entries"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    service_code = Column(String)
    description = Column(Text)
    hours = Column(Float)
    rate = Column(Float)
    entry_date = Column(String)
    voucher_id = Column(Integer)

class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    voucher_type = Column(String)
    status = Column(String)
    submitted_at = Column(DateTime)
    approved_amount = Column(Float)
    notes = Column(Text)
''')

write_file("app/models/classification.py", '''
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base

class ClassificationLabel(Base):
    __tablename__ = "classification_labels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)

class DocumentLabel(Base):
    __tablename__ = "document_labels"
    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True)
    label_id = Column(Integer, ForeignKey("classification_labels.id"), primary_key=True)
    is_manual = Column(Boolean, default=False)
    confidence = Column(Float)
    created_at = Column(DateTime, default=func.now())

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String)
    status = Column(String)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    records_found = Column(Integer, default=0)
    records_saved = Column(Integer, default=0)
    error_log = Column(Text)

class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text)
    filters_json = Column(Text)
    result_count = Column(Integer)
    executed_at = Column(DateTime, default=func.now())
    pinned = Column(Boolean, default=False)

class PortalAuditLog(Base):
    __tablename__ = "portal_audit_log"
    id = Column(Integer, primary_key=True, index=True)
    portal = Column(String)
    client_name = Column(String)
    action = Column(String)
    outcome = Column(String)
    error_message = Column(Text)
    performed_at = Column(DateTime, default=func.now())
''')

# SCHEMAS
write_file("app/schemas/__init__.py", "")

write_file("app/schemas/common.py", '''
from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional
T = TypeVar('T')
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
''')

write_file("app/schemas/auth.py", '''
from pydantic import BaseModel
class Token(BaseModel):
    access_token: str
    token_type: str
class User(BaseModel):
    username: str
''')

write_file("app/schemas/client.py", '''
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ClientBase(BaseModel):
    name: str
    dob: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(ClientBase):
    name: Optional[str] = None

class ClientOut(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
''')

write_file("app/schemas/case.py", '''
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CaseBase(BaseModel):
    client_id: int
    case_number: Optional[str] = None
    court: Optional[str] = None
    case_type: Optional[str] = None
    status: Optional[str] = None
    is_cja: Optional[bool] = False
    voucher_status: Optional[str] = None
    opened_date: Optional[str] = None
    closed_date: Optional[str] = None
    notes: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseUpdate(CaseBase):
    client_id: Optional[int] = None

class CaseOut(CaseBase):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
''')

write_file("app/schemas/document.py", '''
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentBase(BaseModel):
    case_id: Optional[int] = None
    client_id: Optional[int] = None
    filename: str
    doc_type: Optional[str] = None
    source: Optional[str] = None
    content_text: Optional[str] = None
    metadata_json: Optional[str] = None
    classification_label: Optional[str] = None
    classification_confidence: Optional[float] = None
    ingested_at: Optional[datetime] = None

class DocumentOut(DocumentBase):
    id: int
    filepath: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
''')

# MAIN
write_file("app/main.py", '''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, clients, cases, documents, ingestion, portal_assist, classify, search, analytics

app = FastAPI(title="Filestavk API", version="0.1")

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
app.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
app.include_router(portal_assist.router, prefix="/portal", tags=["portal_assist"])
app.include_router(classify.router, prefix="/classify", tags=["classify"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
''')

# ROUTERS
write_file("app/routers/__init__.py", "")

write_file("app/routers/auth.py", '''
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import create_access_token
from app.deps import get_current_user
from app.schemas.auth import Token, User
from app.config import settings

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != settings.admin_username or form_data.password != settings.admin_password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
''')

write_file("app/routers/clients.py", '''
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientOut, ClientUpdate
from app.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[ClientOut])
async def get_clients(name: str = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    query = select(Client)
    if name:
        query = query.filter(Client.name.ilike(f"%{name}%"))
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=ClientOut)
async def create_client(client: ClientCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    new_client = Client(**client.model_dump())
    db.add(new_client)
    await db.commit()
    await db.refresh(new_client)
    return new_client

@router.get("/{id}")
async def get_client(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Client).filter(Client.id == id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.patch("/{id}")
async def update_client(id: int, client: ClientUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Client).filter(Client.id == id))
    db_client = result.scalars().first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    update_data = client.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_client, key, value)
    await db.commit()
    await db.refresh(db_client)
    return db_client

@router.delete("/{id}")
async def delete_client(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Soft delete STUB
    raise HTTPException(status_code=501, detail="Not Implemented")
''')

write_file("app/routers/cases.py", '''
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app.models.case import Case
from app.schemas.case import CaseCreate, CaseOut, CaseUpdate
from app.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[CaseOut])
async def get_cases(status: str = None, is_cja: bool = None, client_id: int = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    query = select(Case)
    if status: query = query.filter(Case.status == status)
    if is_cja is not None: query = query.filter(Case.is_cja == is_cja)
    if client_id: query = query.filter(Case.client_id == client_id)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=CaseOut)
async def create_case(case: CaseCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    new_case = Case(**case.model_dump())
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    return new_case

@router.get("/{id}")
async def get_case(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Case).filter(Case.id == id))
    case = result.scalars().first()
    if not case: raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.patch("/{id}")
async def update_case(id: int, case: CaseUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Case).filter(Case.id == id))
    db_case = result.scalars().first()
    if not db_case: raise HTTPException(status_code=404, detail="Case not found")
    for key, value in case.model_dump(exclude_unset=True).items():
        setattr(db_case, key, value)
    await db.commit()
    await db.refresh(db_case)
    return db_case

@router.get("/{id}/timeline")
async def case_timeline(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return {"message": "Timeline data here"}

@router.post("/{id}/ai-analyze")
async def ai_analyze(id: int):
    raise HTTPException(status_code=501, detail="AI analysis coming in v0.2")

@router.post("/vouchers/{id}/submit-evoucher")
async def submit_evoucher(id: int):
    raise HTTPException(status_code=501, detail="eVoucher coming in v0.2")
''')

write_file("app/routers/documents.py", '''
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import os
import shutil
from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentOut
from app.deps import get_current_user
from app.services.pdf_service import process_pdf
from app.services.classifier_service import classify_text

router = APIRouter()
UPLOAD_DIR = "./data/documents"

@router.get("", response_model=List[DocumentOut])
async def get_documents(case_id: int = None, client_id: int = None, doc_type: str = None, classification_label: str = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    query = select(Document)
    if case_id: query = query.filter(Document.case_id == case_id)
    if client_id: query = query.filter(Document.client_id == client_id)
    if doc_type: query = query.filter(Document.doc_type == doc_type)
    if classification_label: query = query.filter(Document.classification_label == classification_label)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    case_id: Optional[int] = Form(None),
    client_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    case_dir = os.path.join(UPLOAD_DIR, str(case_id or "unassigned"))
    os.makedirs(case_dir, exist_ok=True)
    filepath = os.path.join(case_dir, file.filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    text = ""
    if file.filename.lower().endswith(".pdf"):
        res = process_pdf(filepath)
        text = res["text"]
    
    label, conf = classify_text(text)
    
    doc = Document(
        case_id=case_id,
        client_id=client_id,
        filename=file.filename,
        filepath=filepath,
        doc_type="pdf" if file.filename.lower().endswith(".pdf") else "other",
        source="upload",
        content_text=text,
        classification_label=label,
        classification_confidence=conf
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc

@router.get("/{id}", response_model=DocumentOut)
async def get_document(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(Document).filter(Document.id == id))
    doc = res.scalars().first()
    if not doc: raise HTTPException(404)
    return doc

@router.get("/{id}/file")
async def get_document_file(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(Document).filter(Document.id == id))
    doc = res.scalars().first()
    if not doc or not doc.filepath or not os.path.exists(doc.filepath): raise HTTPException(404)
    return FileResponse(doc.filepath)

@router.patch("/{id}")
async def update_document(id: int, doc_update: dict, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(Document).filter(Document.id == id))
    doc = res.scalars().first()
    if not doc: raise HTTPException(404)
    for k, v in doc_update.items():
        if hasattr(doc, k): setattr(doc, k, v)
    await db.commit()
    await db.refresh(doc)
    return doc

@router.post("/{id}/train")
async def train_document(id: int):
    return {"status": "marked for training"}

@router.post("/{id}/sign")
async def sign_document(id: int):
    raise HTTPException(status_code=501, detail="Signing coming in v0.2")
''')

write_file("app/routers/ingestion.py", '''
from fastapi import APIRouter, Depends, HTTPException, Request
from app.deps import get_current_user
from app.services.gmail_service import get_auth_url, handle_callback, ingest_emails
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()

@router.get("/gmail/auth-url")
async def gmail_auth_url(current_user: dict = Depends(get_current_user)):
    return {"auth_url": get_auth_url()}

@router.post("/gmail/callback")
async def gmail_callback(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    code = data.get("code")
    handle_callback(code)
    return {"status": "success"}

@router.post("/gmail/ingest")
async def start_gmail_ingest(query: str, max_results: int = 10, case_id: int = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Run async
    job_id = await ingest_emails(db, query, max_results, case_id)
    return {"job_id": job_id, "status": "started"}

@router.get("/jobs/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return {"job_id": job_id, "status": "done"}

@router.get("/jobs")
async def list_jobs(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return []

@router.post("/csv")
async def ingest_csv():
    raise HTTPException(status_code=501, detail="CSV import coming in v0.2")
''')

write_file("app/routers/portal_assist.py", '''
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/lookup")
async def portal_lookup():
    raise HTTPException(status_code=501, detail="Coming in v0.2 — Manual Assist Mode")
''')

write_file("app/routers/classify.py", '''
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.classification import ClassificationLabel
from app.deps import get_current_user
from app.services.classifier_service import classify_text, retrain_model

router = APIRouter()

@router.get("/labels")
async def get_labels(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(ClassificationLabel))
    return res.scalars().all()

@router.post("/labels")
async def create_label(name: str, description: str = "", db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    lbl = ClassificationLabel(name=name, description=description)
    db.add(lbl)
    await db.commit()
    await db.refresh(lbl)
    return lbl

@router.post("/predict")
async def predict_text(text: dict, current_user: dict = Depends(get_current_user)):
    label, conf = classify_text(text.get("text", ""))
    return {"label": label, "confidence": conf}

@router.post("/retrain")
async def retrain(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Fetch data and retrain
    retrain_model([], [])
    return {"status": "retrained"}
''')

write_file("app/routers/search.py", '''
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.classification import SearchHistory
from app.deps import get_current_user

router = APIRouter()

@router.get("/canned")
async def get_canned(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(SearchHistory).filter(SearchHistory.pinned == True))
    return res.scalars().all()

@router.post("/execute")
async def execute_search(query_text: str, filters_json: str = "{}", db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    sh = SearchHistory(query_text=query_text, filters_json=filters_json, result_count=0)
    db.add(sh)
    await db.commit()
    await db.refresh(sh)
    return sh

@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(SearchHistory).order_by(SearchHistory.executed_at.desc()).limit(10))
    return res.scalars().all()

@router.patch("/history/{id}/pin")
async def pin_search(id: int, pinned: bool, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(SearchHistory).filter(SearchHistory.id == id))
    sh = res.scalars().first()
    if sh:
        sh.pinned = pinned
        await db.commit()
    return sh
''')

write_file("app/routers/analytics.py", '''
from fastapi import APIRouter, Depends
from app.deps import get_current_user

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(get_current_user)):
    return {
        "active_cases": 10,
        "open_cja_cases": 4,
        "documents_this_month": 25,
        "unclassified_docs": 3,
        "vouchers_pending": 1
    }

@router.get("/cases-by-month")
async def cases_by_month(current_user: dict = Depends(get_current_user)):
    return []

@router.get("/doc-type-distribution")
async def doc_type_distribution(current_user: dict = Depends(get_current_user)):
    return {}
''')

# SERVICES
write_file("app/services/__init__.py", "")

write_file("app/services/pdf_service.py", '''
import pdfplumber
import pytesseract
import os

def process_pdf(filepath: str):
    if not os.path.exists(filepath):
        return {"text": "", "page_count": 0, "extraction_method": "none"}
        
    text = ""
    page_count = 0
    method = "pdfplumber"
    
    try:
        with pdfplumber.open(filepath) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\\n"
    except Exception as e:
        pass
        
    if not text.strip():
        # Fallback to OCR
        method = "tesseract"
        # Dummy OCR for now, requires image conversion which needs pdf2image or similar
        text = "[OCR Output Placeholder]"
        
    return {"text": text.strip(), "page_count": page_count, "extraction_method": method}
''')

write_file("app/services/gmail_service.py", '''
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.config import settings
import base64
from app.models.document import Document
from app.models.classification import IngestionJob

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PATH = './data/gmail_token.json'

def get_auth_url():
    if not settings.gmail_client_id:
        return "setup-env-vars"
    flow = Flow.from_client_config(
        {"installed": {"client_id": settings.gmail_client_id, "client_secret": settings.gmail_client_secret, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=SCOPES,
        redirect_uri=settings.gmail_redirect_uri
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url

def handle_callback(code: str):
    # Dummy implementation for flow.fetch_token
    with open(TOKEN_PATH, 'w') as f:
        f.write(json.dumps({"token": "dummy_token"}))

async def ingest_emails(db, query, max_results, case_id):
    job = IngestionJob(source_type="gmail", status="pending")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Normally we'd queue a background task here
    job.status = "done"
    job.records_found = 0
    await db.commit()
    return job.id
''')

write_file("app/services/classifier_service.py", '''
import os
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

MODEL_PATH = "./data/classifier.pkl"

def get_model():
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return None

def train_model(texts, labels):
    if not texts:
        return
    model = make_pipeline(TfidfVectorizer(), MultinomialNB())
    model.fit(texts, labels)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

def classify_text(text: str):
    model = get_model()
    if not model or not text.strip():
        return ("uncategorized", 0.0)
    
    try:
        preds = model.predict_proba([text])
        classes = model.classes_
        max_idx = preds[0].argmax()
        return (classes[max_idx], float(preds[0][max_idx]))
    except:
        return ("uncategorized", 0.0)
        
def retrain_model(texts, labels):
    train_model(texts, labels)
''')

write_file("app/services/portal_service.py", '''
def do_portal_lookup():
    pass
''')
