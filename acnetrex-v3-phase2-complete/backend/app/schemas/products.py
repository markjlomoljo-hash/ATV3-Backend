from pydantic import BaseModel, Field


class ProductAnalyzeRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    brand: str | None = None
    category: str | None = None
    input_method: str = Field(default="manual")
    raw_ingredient_text: str = Field(min_length=1)


class ProductPatchRequest(BaseModel):
    in_routine: bool | None = None
