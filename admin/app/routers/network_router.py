from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, AuditLog, Network
from app.schemas import NetworkCreate, NetworkOut, NetworkUpdate
from app.services.postfix_service import generate_mynetworks_file

router = APIRouter()


@router.get("", response_model=list[NetworkOut])
def list_networks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Network).order_by(Network.cidr).all()


@router.post("", response_model=NetworkOut, status_code=201)
def create_network(
    body: NetworkCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(Network).filter(Network.cidr == body.cidr).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Netzwerk {body.cidr} existiert bereits")

    network = Network(cidr=body.cidr, owner=body.owner, is_protected=False)
    db.add(network)
    db.flush()

    generate_mynetworks_file(db)

    db.add(AuditLog(
        user_id=user.id,
        action="network_added",
        details=f"Added network {body.cidr} (owner: {body.owner})",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    db.refresh(network)

    return network


@router.put("/{network_id}", response_model=NetworkOut)
def update_network(
    network_id: int,
    body: NetworkUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    network = db.query(Network).filter(Network.id == network_id).first()
    if not network:
        raise HTTPException(status_code=404, detail="Netzwerk nicht gefunden")

    network.owner = body.owner

    db.add(AuditLog(
        user_id=user.id,
        action="network_updated",
        details=f"Updated network {network.cidr} owner to '{body.owner}'",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    db.refresh(network)

    return network


@router.delete("/{network_id}", status_code=200)
def delete_network(
    network_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    network = db.query(Network).filter(Network.id == network_id).first()
    if not network:
        raise HTTPException(status_code=404, detail="Netzwerk nicht gefunden")

    if network.is_protected:
        raise HTTPException(status_code=400, detail=f"Geschuetztes Netzwerk {network.cidr} kann nicht entfernt werden")

    cidr = network.cidr
    db.delete(network)
    db.flush()

    generate_mynetworks_file(db)

    db.add(AuditLog(
        user_id=user.id,
        action="network_removed",
        details=f"Removed network {cidr}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    return {"message": f"Netzwerk {cidr} entfernt"}
