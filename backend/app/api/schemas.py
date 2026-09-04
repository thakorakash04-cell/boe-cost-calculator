from typing import List, Optional
from pydantic import BaseModel, Field

class BOEHeader(BaseModel):
    total_weight_kg: Optional[float] = Field(None, description="Total Weight in Kg")
    exchange_rate: Optional[float] = Field(None, description="Currency Exchange Rate (e.g. USD to INR)")
    invoice_value_fc: Optional[float] = Field(None, description="Total Invoice Value in Foreign Currency")
    freight_inr: Optional[float] = Field(None, description="Total Freight in INR")
    insurance_percent: Optional[float] = Field(None, description="Insurance Percentage")
    misc_charges_fc: Optional[float] = Field(None, description="Miscellaneous Charges in Foreign Currency")
    currency: Optional[str] = Field("USD", description="Invoice Currency")
    boe_number: Optional[str] = Field(None, description="Bill of Entry Number")
    boe_date: Optional[str] = Field(None, description="Bill of Entry Date")

class BOEItem(BaseModel):
    sl_no: int
    material_name: str = Field(..., description="Description of the material")
    unit_price_fc: float = Field(..., description="Unit Price in Foreign Currency")
    quantity: float = Field(..., description="Quantity")
    bcd_rate_percent: float = Field(..., description="Basic Customs Duty Rate Percentage")
    hsn_code: Optional[str] = Field(None, description="HSN Code")
    sws_rate_percent: Optional[float] = Field(10.0, description="Social Welfare Surcharge Rate Percentage (default 10%)")
    igst_rate_percent: Optional[float] = Field(18.0, description="IGST Rate Percentage (default 18%)")

class BOEExtractionRequest(BaseModel):
    filename: str

class BOEExtractionResponse(BaseModel):
    header: BOEHeader
    items: List[BOEItem]
    confidence: float
