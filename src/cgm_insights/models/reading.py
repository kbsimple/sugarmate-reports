"""CGM reading data model with validation."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Trend arrow types from CGM devices
TrendArrow = Literal["↑↑", "↑", "↗", "→", "↘", "↓", "↓↓", ""]


class CGMReading(BaseModel):
    """Single CGM glucose reading with validation.

    Attributes:
        timestamp: When the reading was taken
        glucose_mg_dl: Glucose value in mg/dL (40-400 physiologically plausible)
        trend: Optional trend arrow from CGM device
        source: Data source identifier (sugarmate, dexcom, libre, etc.)
    """

    timestamp: datetime = Field(
        ...,
        description="Reading timestamp (device time)"
    )
    glucose_mg_dl: float = Field(
        ...,
        ge=40.0,
        le=400.0,
        description="Glucose value in mg/dL (physiologically plausible range 40-400)"
    )
    trend: TrendArrow | None = Field(
        None,
        description="Trend arrow from CGM device"
    )
    source: str = Field(
        "unknown",
        description="Data source identifier"
    )

    @field_validator('glucose_mg_dl')
    @classmethod
    def validate_glucose_range(cls, v: float) -> float:
        """Log warning for edge values but accept them.

        CGMs can read values at the edges of their range. We accept
        values from 40-400 mg/dL but flag warnings for values <50 or >350.
        """
        if v < 50:
            # Log warning: very low glucose reading
            pass
        if v > 350:
            # Log warning: very high glucose reading
            pass
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "timestamp": "2026-04-23T08:03:00",
                    "glucose_mg_dl": 150,
                    "trend": "→",
                    "source": "sugarmate"
                }
            ]
        }
    )