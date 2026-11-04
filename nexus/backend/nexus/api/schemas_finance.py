"""Schemi API — Financial Intelligence (Fase 4)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from .schemas import CleanStr, ORMModel, UTCDateTime

SeriesCategory = Literal["stocks", "indices", "bonds", "commodities", "precious_metals", "fx", "crypto", "rates",
                         "inflation", "public_debt", "gdp", "unemployment", "trade_balance", "other"]
Frequency = Literal["D", "W", "M", "Q", "A"]


class SeriesImportIn(BaseModel):
    connector: Literal["world-bank", "fred", "owid", "eurostat"]
    category: SeriesCategory = "other"
    # world-bank: indicator + country · fred: series_id · owid: slug + entity · eurostat: dataset + filters
    indicator: str | None = None
    country: str | None = None
    series_id: str | None = None
    slug: str | None = None
    entity: str | None = None
    dataset: str | None = None
    filters: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _required(self):
        need = {"world-bank": ("indicator", "country"), "fred": ("series_id",), "owid": ("slug", "entity"), "eurostat": ("dataset",)}
        missing = [f for f in need[self.connector] if not getattr(self, f)]
        if missing:
            raise ValueError(f"Campi obbligatori per {self.connector}: {', '.join(missing)}")
        return self


class SeriesOut(ORMModel):
    id: int
    name: str
    category: str
    country: str
    connector: str
    source_series_id: str
    source_label: str
    source_url: str
    license_note: str
    unit: str
    frequency: Frequency
    start_date: str | None
    end_date: str | None
    source_last_updated: str
    retrieved_at: UTCDateTime | None
    from_cache: bool
    observation_count: int
    missing_count: int
    description: str
    is_demo: bool
    last_value: float | None = None
    last_date: str | None = None
    created_at: UTCDateTime


class ObservationOut(BaseModel):
    date: str
    value: float | None


class SeriesDetailOut(SeriesOut):
    observations: list[ObservationOut]
    import_warnings: list[str] = Field(default_factory=list)


class SeriesUpdate(BaseModel):
    name: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)] | None = None
    category: SeriesCategory | None = None


class CompareIn(BaseModel):
    series_ids: list[int] = Field(min_length=2, max_length=8)
    target_frequency: Frequency | None = None
    method: Literal["last", "mean", "sum"] = "last"
    mode: Literal["returns", "levels"] = "returns"


class CredentialIn(BaseModel):
    provider: Literal["fred", "openai-compatible", "anthropic", "ollama"]
    secret: Annotated[str, StringConstraints(max_length=500)] = ""
    base_url: Annotated[str, StringConstraints(max_length=300)] = ""
    model: Annotated[str, StringConstraints(max_length=120)] = ""


class CredentialOut(BaseModel):
    provider: str
    configured: bool
    hint: str
    config: dict
    updated_at: UTCDateTime | None


class Preset(BaseModel):
    connector: str
    label: str
    category: SeriesCategory
    params: dict
