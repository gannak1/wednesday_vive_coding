from pydantic import BaseModel, Field


class SaveArticleRequest(BaseModel):
    article_id: str = Field(min_length=1)
