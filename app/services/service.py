from typing import List, Optional
from app.models.example import ExampleCreate, ExampleResponse

#Base para la lógica del negocio
class ExampleService:
    def __init__(self):
        pass

    def create(self, data: ExampleCreate):
        pass

    def get_by_id(self, item_id: int):
        pass