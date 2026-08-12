from dataclasses import dataclass, field


@dataclass
class FactChunk:
    chunk_index: int
    text: str
    input_chars: int
    source_blocks: list[str] = field(default_factory=list)
    context_header: str = ""
    oversized: bool = False


@dataclass
class FactChunkResult:
    chunk_index: int
    input_chars: int
    fact_count: int = 0
    elapsed: float = 0.0
    success: bool = True
    error: str = ""
    data: dict | None = None
    usage: dict = field(default_factory=dict)


class FactChunkExecutionError(RuntimeError):
    def __init__(self, failures: list[FactChunkResult]):
        self.failures = failures
        message = "; ".join(
            f"chunk {failure.chunk_index}: {failure.error}"
            for failure in failures
        )
        super().__init__(
            f"Facts chunk extraction failed: {message}"
        )
