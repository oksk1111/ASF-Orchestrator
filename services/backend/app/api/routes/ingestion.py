from fastapi import APIRouter

from app.services.container import ingestion_service

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/sync")
def sync_ingestion() -> dict:
    return ingestion_service.sync_public_data()
