from pydantic import BaseModel


class ClipInput(BaseModel):
    source: int | str
    start: float | None = 0
    end: float | None = None


class AssemblyCreate(BaseModel):
    name: str | None = None
    clips: list[ClipInput]
    preview: bool = True


class ClipDetail(BaseModel):
    pos: int
    filename: str
    start: float
    end: float
    duration: float


class AssemblyUpdate(BaseModel):
    note: str | None = None


class Assembly(BaseModel):
    id: str
    name: str | None = None
    status: str = "processing"
    error: str | None = None
    preview: bool = True
    clips: list[ClipDetail] = []
    output_url: str | None = None
    duration: float | None = None
    note: str | None = None
    created: str
