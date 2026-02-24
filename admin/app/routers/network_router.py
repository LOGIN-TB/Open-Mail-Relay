from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, AuditLog
from app.schemas import NetworkEntry, NetworkList
from app.services.postfix_service import read_mynetworks, add_network, remove_network

router = APIRouter()


@router.get("", response_model=NetworkList)
def list_networks(user: User = Depends(get_current_user)):
    return NetworkList(networks=read_mynetworks())


@router.post("", status_code=201)
def create_network(
    body: NetworkEntry,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success, message = add_network(body.cidr)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    db.add(AuditLog(
        user_id=user.id,
        action="network_added",
        details=f"Added network {body.cidr}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    return {"message": message}


@router.delete("/{cidr:path}", status_code=200)
def delete_network(
    cidr: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success, message = remove_network(cidr)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    db.add(AuditLog(
        user_id=user.id,
        action="network_removed",
        details=f"Removed network {cidr}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    return {"message": message}
