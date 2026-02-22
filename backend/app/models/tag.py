from pydantic import BaseModel


class Tag(BaseModel):
    id: int
    name: str
    color: str


class TagCreate(BaseModel):
    name: str
    color: str = "#839496"


class TagUpdate(BaseModel):
    name: str
