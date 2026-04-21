from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

import simfile


SIMFILE_EXTENSIONS = (".ssc", ".sm")
SPLIT_TIMING_KEYS = ("OFFSET", "BPMS", "STOPS", "DELAYS", "WARPS")
BASE_TARGET = "base"


@dataclass(frozen=True)
class SimfileRow:
    path: Path
    target: str
    title: str
    artist: str
    slot: str
    chart_index: int | None
    has_own_offset: bool
    has_split_timing: bool
    effective_offset: float


@dataclass(frozen=True)
class AdjustmentRequest:
    path: Path
    target: str
    chart_index: int | None = None


@dataclass(frozen=True)
class AdjustmentResult:
    path: Path
    target: str
    old_offset: float | None
    new_offset: float | None
    changed: bool
    message: str


@dataclass(frozen=True)
class SimfileLoadError:
    path: Path
    title: str
    error: str


@dataclass(frozen=True)
class ScanResult:
    rows: list[SimfileRow]
    errors: list[SimfileLoadError]


def discover_simfiles(root: str | Path) -> list[Path]:
    root_path = Path(root).expanduser()
    if root_path.is_file():
        if root_path.suffix.lower() in SIMFILE_EXTENSIONS:
            return [root_path.resolve()]
        return []

    if not root_path.exists():
        return []

    paths: list[Path] = []
    for directory, _, filenames in os.walk(root_path):
        selected = choose_simfile(Path(directory), filenames)
        if selected is not None:
            paths.append(selected.resolve())
    return sorted(paths, key=lambda p: str(p).lower())


def choose_simfile(directory: Path, filenames: Iterable[str]) -> Path | None:
    candidates = [
        directory / filename
        for filename in filenames
        if Path(filename).suffix.lower() in SIMFILE_EXTENSIONS
    ]
    if not candidates:
        return None

    ssc_files = sorted(p for p in candidates if p.suffix.lower() == ".ssc")
    if ssc_files:
        return ssc_files[0]

    sm_files = sorted(p for p in candidates if p.suffix.lower() == ".sm")
    return sm_files[0] if sm_files else None


def scan_path(root: str | Path) -> ScanResult:
    rows: list[SimfileRow] = []
    errors: list[SimfileLoadError] = []
    for path in discover_simfiles(root):
        try:
            rows.extend(scan_simfile(path))
        except Exception as exc:
            errors.append(
                SimfileLoadError(
                    path=path,
                    title=error_title(path),
                    error=format_error(exc),
                )
            )
    return ScanResult(rows=rows, errors=errors)


def scan_simfile(path: str | Path) -> list[SimfileRow]:
    simfile_path = Path(path).resolve()
    sm = simfile.open(str(simfile_path), strict=False)
    base_offset = parse_offset(sm.offset)
    title = text_value(getattr(sm, "title", ""))
    artist = text_value(getattr(sm, "artist", ""))

    rows = [
        SimfileRow(
            path=simfile_path,
            target=BASE_TARGET,
            title=title,
            artist=artist,
            slot="*",
            chart_index=None,
            has_own_offset=True,
            has_split_timing=False,
            effective_offset=base_offset,
        )
    ]

    for chart_index, chart in enumerate(sm.charts):
        has_split_timing = chart_has_split_timing(chart)
        if not has_split_timing:
            continue

        has_own_offset = "OFFSET" in chart
        effective_offset = parse_offset(chart.get("OFFSET", sm.offset))
        rows.append(
            SimfileRow(
                path=simfile_path,
                target=f"chart:{chart_index}",
                title=title,
                artist=artist,
                slot=chart_label(chart, chart_index),
                chart_index=chart_index,
                has_own_offset=has_own_offset,
                has_split_timing=has_split_timing,
                effective_offset=effective_offset,
            )
        )

    return rows


def apply_adjustments(
    requests: Iterable[AdjustmentRequest],
    delta_ms: float,
    make_backup: bool = True,
) -> list[AdjustmentResult]:
    requests_by_path: dict[Path, list[AdjustmentRequest]] = {}
    for request in requests:
        requests_by_path.setdefault(request.path.resolve(), []).append(request)

    results: list[AdjustmentResult] = []
    delta_seconds = delta_ms / 1000.0
    for path in sorted(requests_by_path):
        path_requests = dedupe_requests(requests_by_path[path])
        mutate_kwargs = {"strict": False}
        if make_backup:
            mutate_kwargs["backup_filename"] = str(path) + ".oldsync"

        with simfile.mutate(str(path), **mutate_kwargs) as sm:
            base_selected = any(request.target == BASE_TARGET for request in path_requests)
            original_base_offset = parse_offset(sm.offset)

            for request in path_requests:
                if request.target == BASE_TARGET:
                    new_offset = original_base_offset + delta_seconds
                    sm.offset = format_offset(new_offset)
                    results.append(
                        AdjustmentResult(
                            path=path,
                            target=BASE_TARGET,
                            old_offset=original_base_offset,
                            new_offset=new_offset,
                            changed=True,
                            message="Adjusted top-level OFFSET.",
                        )
                    )
                    continue

                chart_index = request.chart_index
                if chart_index is None:
                    results.append(
                        AdjustmentResult(
                            path=path,
                            target=request.target,
                            old_offset=None,
                            new_offset=None,
                            changed=False,
                            message="Skipped chart request without a chart index.",
                        )
                    )
                    continue

                if chart_index < 0 or chart_index >= len(sm.charts):
                    results.append(
                        AdjustmentResult(
                            path=path,
                            target=request.target,
                            old_offset=None,
                            new_offset=None,
                            changed=False,
                            message=f"Skipped missing chart index {chart_index}.",
                        )
                    )
                    continue

                chart = sm.charts[chart_index]
                if base_selected and "OFFSET" not in chart:
                    results.append(
                        AdjustmentResult(
                            path=path,
                            target=request.target,
                            old_offset=original_base_offset,
                            new_offset=original_base_offset + delta_seconds,
                            changed=False,
                            message="Skipped chart without its own OFFSET because the selected base OFFSET already affects it.",
                        )
                    )
                    continue

                old_offset = parse_offset(chart.get("OFFSET", sm.offset))
                new_offset = old_offset + delta_seconds
                chart["OFFSET"] = format_offset(new_offset)
                results.append(
                    AdjustmentResult(
                        path=path,
                        target=request.target,
                        old_offset=old_offset,
                        new_offset=new_offset,
                        changed=True,
                        message="Adjusted chart OFFSET.",
                    )
                )

    return results


def dedupe_requests(requests: Iterable[AdjustmentRequest]) -> list[AdjustmentRequest]:
    seen: set[tuple[Path, str, int | None]] = set()
    deduped: list[AdjustmentRequest] = []
    for request in requests:
        key = (request.path.resolve(), request.target, request.chart_index)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(request)
    return deduped


def chart_has_split_timing(chart) -> bool:
    return any(key in chart for key in SPLIT_TIMING_KEYS)


def chart_label(chart, chart_index: int) -> str:
    steps_type = text_value(chart.get("STEPSTYPE", "?"))
    difficulty = text_value(chart.get("DIFFICULTY", "?"))
    description = text_value(chart.get("DESCRIPTION", ""))
    label = f"{chart_index}: {steps_type} / {difficulty}"
    if description:
        label += f" / {description}"
    return label


def parse_offset(value) -> float:
    if value is None or value == "":
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'Invalid OFFSET value "{value}"') from exc


def format_offset(value: float) -> str:
    return f"{value:0.3f}"


def text_value(value) -> str:
    return "" if value is None else str(value)


def error_title(path: Path) -> str:
    parent_name = path.parent.name
    return parent_name or path.stem or path.name


def format_error(exc: Exception) -> str:
    error_text = str(exc).strip()
    if error_text:
        return f"{type(exc).__name__}: {error_text}"
    return type(exc).__name__
