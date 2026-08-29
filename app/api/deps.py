from sqlalchemy.orm import Session
from fastapi import Depends

from app.db import get_db
from app.store.event_store import EventStore


def get_store(db: Session = Depends(get_db)) -> EventStore:
    return EventStore(db)
