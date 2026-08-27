from pydantic import BaseModel, Field


class CreateAccessRequestRequest(BaseModel):
    institution_name: str = Field(..., min_length=1, max_length=255)
    contact_name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    role_interested: str | None = Field(default=None, max_length=100)
    message: str | None = Field(default=None, max_length=2000)


class AccessRequestAck(BaseModel):
    status: str = "received"
