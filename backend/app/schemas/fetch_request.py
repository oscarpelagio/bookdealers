from sqlmodel import SQLModel

class FetchRequest(SQLModel):
    url: str
    params: dict
