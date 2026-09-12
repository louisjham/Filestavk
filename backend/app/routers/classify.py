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
