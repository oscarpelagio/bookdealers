from sqlmodel import SQLModel, Field, UniqueConstraint

class Search(SQLModel, table=True):
    __tablename__ = "search_query"
    
    id: int | None = Field(default=None, primary_key=True)
    query : str = Field(index=True, unique=True)


class SearchRelation(SQLModel, table=True):
    __tablename__ = "search_cache"
    __table_args__ = (UniqueConstraint("id_book", "id_search", name="unique_relation"),)
    
    id: int | None = Field(default=None, primary_key=True)
    id_book : int = Field(foreign_key="books.id")
    id_search : int = Field(foreign_key="search_query.id")
