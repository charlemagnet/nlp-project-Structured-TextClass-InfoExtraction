from typing import Literal
from pydantic import BaseModel, ConfigDict

class NewsAnalysis(BaseModel):

    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "World", "Sports", "Business", "Sci/Tech"
    ]

    persons: list[str]
    organizations: list[str]
    locations: list[str]