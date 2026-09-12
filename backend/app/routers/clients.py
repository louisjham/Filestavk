from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, delete, update
from typing import List, Optional
import re

from app.database import get_db
from app.models.client import Client
from app.models.case import Case
from app.models.document import Document
from app.schemas.client import ClientCreate, ClientOut, ClientUpdate
from app.deps import get_current_user
from app.services.deduplication_service import run_full_database_deduplication, normalize_name

router = APIRouter()


@router.get("", response_model=List[ClientOut])
async def get_clients(
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all client profiles enriched with linked case counts and cause numbers."""
    query = select(Client).options(selectinload(Client.cases)).order_by(Client.name.asc())
    if name:
        query = query.filter(Client.name.ilike(f"%{name}%"))
    result = await db.execute(query)
    clients = result.scalars().all()

    output = []
    for cl in clients:
        cases = cl.cases or []
        case_nums = [c.case_number for c in cases if c.case_number]
        has_active = any(c.status in ("open", "OPEN", "APPOINTED", "PENDING") for c in cases)
        in_custody = any(bool(c.in_custody) for c in cases)
        output.append(
            ClientOut(
                id=cl.id,
                name=cl.name,
                dob=cl.dob,
                address=cl.address,
                phone=cl.phone,
                email=cl.email,
                notes=cl.notes,
                case_count=len(cases),
                case_numbers=case_nums,
                has_active_cases=has_active,
                is_in_custody=in_custody,
                created_at=cl.created_at,
            )
        )
    return output


@router.post("", response_model=ClientOut)
async def create_client(
    client_in: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Find-or-create client profile with case-insensitive and whitespace-normalized deduplication.
    If a client with the same name already exists, enriches missing contact details and returns existing.
    """
    norm_name = normalize_name(client_in.name)
    
    # Check for existing matching client
    res = await db.execute(select(Client).options(selectinload(Client.cases)))
    all_clients = res.scalars().all()
    
    existing_client = next((c for c in all_clients if normalize_name(c.name) == norm_name), None)

    if existing_client:
        # Merge missing fields
        if not existing_client.dob and client_in.dob:
            existing_client.dob = client_in.dob
        if not existing_client.phone and client_in.phone:
            existing_client.phone = client_in.phone
        if not existing_client.email and client_in.email:
            existing_client.email = client_in.email
        if (not existing_client.address or existing_client.address == "Corpus Christi, TX") and client_in.address and client_in.address != "Corpus Christi, TX":
            existing_client.address = client_in.address
        if client_in.notes and (not existing_client.notes or client_in.notes not in existing_client.notes):
            if not existing_client.notes:
                existing_client.notes = client_in.notes
            else:
                existing_client.notes += f" | {client_in.notes}"
        
        await db.commit()
        await db.refresh(existing_client)
        cases = existing_client.cases or []
        return ClientOut(
            id=existing_client.id,
            name=existing_client.name,
            dob=existing_client.dob,
            address=existing_client.address,
            phone=existing_client.phone,
            email=existing_client.email,
            notes=existing_client.notes,
            case_count=len(cases),
            case_numbers=[c.case_number for c in cases if c.case_number],
            has_active_cases=any(c.status in ("open", "OPEN", "APPOINTED", "PENDING") for c in cases),
            is_in_custody=any(c.in_custody for c in cases),
            created_at=existing_client.created_at,
        )

    create_data = client_in.model_dump()
    create_data.pop("in_custody", None)
    new_client = Client(**create_data)
    db.add(new_client)
    await db.commit()
    await db.refresh(new_client)
    return ClientOut(
        id=new_client.id,
        name=new_client.name,
        dob=new_client.dob,
        address=new_client.address,
        phone=new_client.phone,
        email=new_client.email,
        notes=new_client.notes,
        case_count=0,
        case_numbers=[],
        has_active_cases=False,
        is_in_custody=False,
        created_at=new_client.created_at,
    )


@router.post("/deduplicate")
async def deduplicate_clients(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    1-Click Database Deduplication & Consolidation:
    Scans SQLite for duplicate client and case names, merges demographic & contact info into canonical records,
    re-links all child cases, documents, events, vouchers, and time entries, and deletes redundant orphaned records.
    """
    report = await run_full_database_deduplication(db)
    return report


@router.get("/{id}")
async def get_client(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Client).options(selectinload(Client.cases)).filter(Client.id == id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    cases = client.cases or []
    in_custody = any(bool(c.in_custody) for c in cases)
    return {
        "id": client.id,
        "name": client.name,
        "dob": client.dob,
        "address": client.address,
        "phone": client.phone,
        "email": client.email,
        "notes": client.notes,
        "created_at": client.created_at,
        "is_in_custody": in_custody,
        "cases": [
            {
                "id": c.id,
                "case_number": c.case_number,
                "court": c.court,
                "judge": c.judge,
                "charge_description": c.charge_description,
                "status": c.status,
                "stage": c.stage,
                "in_custody": c.in_custody,
                "jail_facility": c.jail_facility,
                "is_cja": c.is_cja,
                "has_appointment_order": c.has_appointment_order,
                "has_appointment_acceptance": c.has_appointment_acceptance,
                "appointment_status": c.appointment_status,
            }
            for c in cases
        ],
    }


@router.patch("/{id}")
async def update_client(
    id: int,
    client: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Client).filter(Client.id == id))
    db_client = result.scalars().first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    update_data = client.model_dump(exclude_unset=True)
    custody_update = update_data.pop("in_custody", None)
    if custody_update is not None:
        await db.execute(
            update(Case).where(Case.client_id == id).values(in_custody=custody_update)
        )
    for key, value in update_data.items():
        setattr(db_client, key, value)
    await db.commit()
    await db.refresh(db_client)
    return db_client


@router.delete("/{id}")
async def delete_client(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a client and unbind associated cases and documents."""
    result = await db.execute(select(Client).filter(Client.id == id))
    db_client = result.scalars().first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Unlink cases & documents
    await db.execute(update(Case).where(Case.client_id == id).values(client_id=None))
    await db.execute(update(Document).where(Document.client_id == id).values(client_id=None))
    await db.execute(delete(Client).where(Client.id == id))
    await db.commit()
    return {"success": True, "message": f"Client #{id} ('{db_client.name}') deleted successfully."}
