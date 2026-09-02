"""Project-specific exception boundary."""


class DataLayoutError(Exception):
    """Raised when the official Multimodal data layout is invalid."""


class ConfigurationError(Exception):
    """Raised when runtime configuration is missing or invalid."""


class ModelLoadError(Exception):
    """Raised when a local model cannot be loaded."""


class InferenceError(Exception):
    """Raised when model inference fails."""


class ParseError(Exception):
    """Raised when generated model output cannot be parsed."""


class ComplianceError(Exception):
    """Raised when a run violates compliance requirements."""


class SubmissionFormatError(Exception):
    """Raised when a submission artifact is malformed."""


class CandidateEligibilityError(Exception):
    """Raised when a candidate cannot enter the smoke harness."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")
