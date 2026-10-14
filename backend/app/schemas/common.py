from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

Role = Literal["admin", "analyst", "viewer"]

# Passwords are taken verbatim: trimming would silently change the secret (04 §1.5 trims strings).
Password = Annotated[str, StringConstraints(strip_whitespace=False, min_length=1, max_length=255)]
NewPassword = Annotated[
    str, StringConstraints(strip_whitespace=False, min_length=12, max_length=255)
]
Name = Annotated[str, StringConstraints(min_length=1)]


class RequestModel(BaseModel):
    """Request bodies: unknown fields rejected, strings trimmed, 255 chars max (04 §1.5)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, str_max_length=255)


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
