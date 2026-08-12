from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter

from facts.merge import merge_fact_chunk_results
from facts.models import FactChunkExecutionError, FactChunkResult


def _fact_count(data) -> int:
    if isinstance(data, dict) and isinstance(data.get("facts"), list):
        return len(data["facts"])
    return 0


def _run_one_chunk(chunk, extract_one):
    started = perf_counter()
    try:
        data = extract_one(chunk.text)
        if not isinstance(data, dict) or not isinstance(data.get("facts"), list):
            raise ValueError("Fact chunk did not return a valid facts list")
        return FactChunkResult(
            chunk_index=chunk.chunk_index,
            input_chars=chunk.input_chars,
            fact_count=_fact_count(data),
            elapsed=round(perf_counter() - started, 3),
            success=True,
            data=data,
        )
    except Exception as exc:
        return FactChunkResult(
            chunk_index=chunk.chunk_index,
            input_chars=chunk.input_chars,
            elapsed=round(perf_counter() - started, 3),
            success=False,
            error=str(exc),
            data=None,
        )


def execute_fact_chunks(chunks, extract_one, max_concurrency=2):
    if not chunks:
        return {
            "facts": [],
            "info_gaps": [],
            "chunk_report": {
                "raw_facts": 0,
                "exact_duplicates_removed": 0,
                "final_facts": 0,
                "duplicate_records": [],
                "chunks": [],
                "request_count": 0,
                "max_concurrency": max_concurrency,
                "wall_time": 0,
            },
        }

    max_workers = max(
        1,
        min(int(max_concurrency or 1), len(chunks)),
    )
    started = perf_counter()
    results = []

    if max_workers == 1:
        for chunk in chunks:
            results.append(
                _run_one_chunk(chunk, extract_one)
            )
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(_run_one_chunk, chunk, extract_one): chunk
                for chunk in chunks
            }
            for future in as_completed(future_map):
                results.append(future.result())

    failures = [
        result
        for result in results
        if not result.success
    ]
    if failures:
        raise FactChunkExecutionError(failures)

    merged = merge_fact_chunk_results(results)
    wall_time = round(perf_counter() - started, 3)
    merged.setdefault("chunk_report", {})
    merged["chunk_report"].update(
        {
            "chunks": [
                {
                    "chunk_index": result.chunk_index,
                    "input_chars": result.input_chars,
                    "fact_count": result.fact_count,
                    "elapsed": result.elapsed,
                    "success": result.success,
                    "error": result.error,
                }
                for result in sorted(results, key=lambda item: item.chunk_index)
            ],
            "request_count": len(chunks),
            "max_concurrency": max_workers,
            "wall_time": wall_time,
        }
    )
    return merged
