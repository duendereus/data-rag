"""Custom exception classes mapped to HTTP status codes."""


class DatasetNotFoundError(Exception):
    """Raised when a dataset ID does not exist."""

    def __init__(self, dataset_id: str) -> None:
        self.dataset_id = dataset_id
        super().__init__(f"Dataset not found: {dataset_id}")


class UnsupportedFileTypeError(Exception):
    """Raised when an uploaded file has an unsupported extension."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__(f"Unsupported file type: {filename}")


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the size limit."""

    def __init__(self, size_mb: float, max_mb: int) -> None:
        self.size_mb = size_mb
        self.max_mb = max_mb
        super().__init__(f"File size {size_mb:.1f}MB exceeds limit of {max_mb}MB")


class QueryExecutionError(Exception):
    """Raised when DuckDB fails to execute generated SQL."""

    def __init__(self, sql: str, detail: str) -> None:
        self.sql = sql
        self.detail = detail
        super().__init__(f"Query execution failed: {detail}")


class LLMError(Exception):
    """Raised when the LLM provider returns an error."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(f"LLM error: {detail}")


class SchemaExtractionError(Exception):
    """Raised when schema extraction from a file fails."""

    def __init__(self, file_path: str, detail: str) -> None:
        self.file_path = file_path
        self.detail = detail
        super().__init__(f"Schema extraction failed for {file_path}: {detail}")
