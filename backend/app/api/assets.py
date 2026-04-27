"""Asset watchlist API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_db
from app.models.asset import Asset, AssetCreate, AssetUpdate

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/")
def list_assets(db: Session = Depends(get_db)):
    assets = db.query(Asset).filter(Asset.active == True).all()
    return [
        {
            "id": a.id,
            "symbol": a.symbol,
            "name": a.name,
            "exchange": a.exchange,
            "asset_type": a.asset_type,
            "active": a.active,
        }
        for a in assets
    ]


@router.post("/")
def add_asset(asset_in: AssetCreate, db: Session = Depends(get_db)):
    asset = Asset(
        symbol=asset_in.symbol,
        name=asset_in.name or asset_in.symbol,
        exchange=asset_in.exchange or "HYPERLIQUID",
        asset_type=asset_in.asset_type or "crypto",
        active=True,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"id": asset.id, "symbol": asset.symbol, "name": asset.name}


@router.delete("/{asset_id}")
def remove_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()
    return {"message": "Asset removed"}
