from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from database.models import EventLog


def record_event(
    db: Session,
    user_id: Optional[int],
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    db.add(EventLog(user_id=user_id, event_type=event_type, payload=payload))
    db.commit()
