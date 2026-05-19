from pydantic import BaseModel


class RuntimeErrorResult(BaseModel):
    success: bool = False
    error_code: str
    message: str
    retryable: bool = False


class CapabilityTypeError(RuntimeError):
    pass
