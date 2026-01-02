from typing import Optional

from pydantic import BaseModel


class ToggleResponse(BaseModel):
  liked: Optional[bool] = None
  followed: Optional[bool] = None


class SimpleMessage(BaseModel):
  message: str
