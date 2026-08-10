from pydantic import BaseModel
from datetime import datetime
from typing import Optional

#Base vacía para los modelos de Pydantic

class ExampleBase(BaseModel):
    title: str

class ExampleCreate(ExampleBase):
    pass

class ExampleResponse(ExampleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True