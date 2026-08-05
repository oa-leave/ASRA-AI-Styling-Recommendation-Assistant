from typing import Any, Dict

from pydantic import BaseModel, ConfigDict


class HistoryResponse(BaseModel):
    id: int
    user_id: int
    request_context: Dict[str, Any]
    response_snapshot: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
