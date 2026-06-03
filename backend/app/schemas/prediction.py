"""预测相关 schemas"""
from pydantic import BaseModel, Field


class StockPredictionRequest(BaseModel):
    code: str = Field(..., description="股票代码或名称")
    horizon: str = Field(..., description="预测时段：tomorrow / week / 1m / 3m")


class IndustryPredictionRequest(BaseModel):
    name: str = Field(..., description="行业板块名称")


class SavePredictionRequest(BaseModel):
    pass  # 只需要 prediction_id 在路径中


class PredictionOut(BaseModel):
    id: str
    type: str
    code: str = ""
    name: str
    horizon: str = ""
    prediction_content: str
    confidence_label: str = ""
    status: str = ""
    created_at: str | None = None

    class Config:
        from_attributes = True


class PredictionDetailOut(PredictionOut):
    data_snapshot: dict | None = None
    reviews: list["ReviewOut"] = []


class ReviewOut(BaseModel):
    id: str
    prediction_id: str
    review_type: str
    accuracy_rating: str = ""
    deviation_reason: str = ""
    review_content: str
    created_at: str | None = None

    class Config:
        from_attributes = True


class PredictionListOut(BaseModel):
    items: list[PredictionOut]
    total: int


class DataEngineResult(BaseModel):
    """数据引擎输出"""
    structured_data: dict
    confidence_label: str  # 高/中/低
    source_urls: list[str]
    fetch_timestamp: str
