from pydantic import BaseModel, model_validator


class AdminUserUpdate(BaseModel):
    is_platform_admin: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "AdminUserUpdate":
        if self.is_platform_admin is None and self.is_active is None:
            raise ValueError("At least one user property is required")
        return self
