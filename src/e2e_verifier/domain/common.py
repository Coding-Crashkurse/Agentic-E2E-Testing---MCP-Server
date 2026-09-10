from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

IDENTIFIER_PATTERN = r"^[A-Za-z0-9._-]{1,64}$"
RUN_ID_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"

type Identifier = Annotated[str, Field(pattern=IDENTIFIER_PATTERN)]
type TimeoutMs = Annotated[int, Field(ge=100, le=120_000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)
