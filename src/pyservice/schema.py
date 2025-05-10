import uuid

from pydantic import BaseModel, ConfigDict
from pydantic_extra_types.pendulum_dt import DateTime


class EntityModel(BaseModel):
    id: uuid.UUID
    created_at: DateTime
    updated_at: DateTime

    model_config = ConfigDict(from_attributes=True)


class ActionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
