from pydantic import BaseModel


class SourceTag(BaseModel):
    name: str
    color: str


class Source(BaseModel):
    index: int
    filename: str
    duration: float
    resolution: str
    codec: str
    file_size: int
    tags: list[SourceTag] = []
