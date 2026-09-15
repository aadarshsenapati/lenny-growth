class AppError(Exception):
    """Base class for all handled application errors. Carries an HTTP status
    and a stable machine-readable code so the frontend can branch on it."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class SessionNotFoundError(AppError):
    status_code = 404
    code = "session_not_found"


class ArtifactNotFoundError(AppError):
    status_code = 404
    code = "artifact_not_found"


class LLMProviderUnavailableError(AppError):
    status_code = 503
    code = "llm_provider_unavailable"


class LLMTimeoutError(AppError):
    status_code = 504
    code = "llm_timeout"


class RetrievalIndexMissingError(AppError):
    status_code = 503
    code = "retrieval_index_missing"


class ArtifactRenderingError(AppError):
    status_code = 422
    code = "artifact_rendering_error"


class DatabaseUnavailableError(AppError):
    status_code = 503
    code = "database_unavailable"
