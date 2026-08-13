from pydantic import BaseModel, ConfigDict, Field

from app.modules.products.schemas import ProductSummary


class ProductRecognitionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    recognized_code: str = Field(alias="recognizedCode")
    confidence: float
    product: ProductSummary
