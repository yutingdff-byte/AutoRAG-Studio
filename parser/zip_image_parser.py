from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Iterable

from parser.image_parser import IMAGE_EXTENSIONS, parse_image
from utils.config import get_config


ZIP_EXTENSIONS = {".zip"}

SYSTEM_FILE_NAMES = {
    ".ds_store",
    "thumbs.db",
}

SYSTEM_DIR_NAMES = {
    "__macosx",
}

DEFAULT_MAX_ENTRIES = 500
DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES = 768 * 1024 * 1024
DEFAULT_MAX_ENTRY_BYTES = 120 * 1024 * 1024
DEFAULT_MAX_COMPRESSION_RATIO = 100
DEFAULT_MAX_NESTED_ZIPS = 30


@dataclass(frozen=True)
class ZipImageItem:
    source_archive: str
    relative_path: str
    material_group: str
    source_filename: str
    data: bytes
    depth: int = 0

    @property
    def name(self) -> str:
        return self.source_filename

    def getvalue(self) -> bytes:
        return self.data


@dataclass(frozen=True)
class ZipUnsupportedItem:
    relative_path: str
    reason: str


@dataclass
class ZipImageInventory:
    source_archive: str
    images: list[ZipImageItem] = field(default_factory=list)
    unsupported: list[ZipUnsupportedItem] = field(default_factory=list)
    inner_zip_count: int = 0
    total_uncompressed_bytes: int = 0
    entry_count: int = 0

    @property
    def image_count(self) -> int:
        return len(self.images)


class ZipImageParseError(ValueError):
    pass


class _ZipBudget:
    def __init__(self):
        self.max_entries = _int_config(
            "ZIP_IMAGE_MAX_ENTRIES",
            DEFAULT_MAX_ENTRIES,
        )
        self.max_total_uncompressed_bytes = _int_config(
            "ZIP_IMAGE_MAX_TOTAL_UNCOMPRESSED_BYTES",
            DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES,
        )
        self.max_entry_bytes = _int_config(
            "ZIP_IMAGE_MAX_ENTRY_BYTES",
            DEFAULT_MAX_ENTRY_BYTES,
        )
        self.max_compression_ratio = _int_config(
            "ZIP_IMAGE_MAX_COMPRESSION_RATIO",
            DEFAULT_MAX_COMPRESSION_RATIO,
        )
        self.max_nested_zips = _int_config(
            "ZIP_IMAGE_MAX_NESTED_ZIPS",
            DEFAULT_MAX_NESTED_ZIPS,
        )
        self.entry_count = 0
        self.total_uncompressed_bytes = 0
        self.nested_zip_count = 0

    def record_entry(self, info: zipfile.ZipInfo, relative_path: str) -> None:
        self.entry_count += 1
        if self.entry_count > self.max_entries:
            raise ZipImageParseError(
                f"ZIP文件数量超过限制：最多 {self.max_entries} 个条目"
            )

        if info.file_size > self.max_entry_bytes:
            raise ZipImageParseError(
                f"ZIP内文件超过单文件限制：{relative_path}"
            )

        self.total_uncompressed_bytes += info.file_size
        if self.total_uncompressed_bytes > self.max_total_uncompressed_bytes:
            raise ZipImageParseError(
                "ZIP累计解压大小超过限制"
            )

        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > self.max_compression_ratio:
                raise ZipImageParseError(
                    f"ZIP压缩比异常，疑似ZIP Bomb：{relative_path}"
                )

    def record_nested_zip(self, relative_path: str) -> None:
        self.nested_zip_count += 1
        if self.nested_zip_count > self.max_nested_zips:
            raise ZipImageParseError(
                f"内层ZIP数量超过限制：{relative_path}"
            )


def _int_config(name: str, default: int) -> int:
    raw = get_config(
        name,
        str(default),
    )
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _get_source_name(file) -> str:
    if isinstance(file, (str, Path)):
        return Path(file).name
    return Path(str(getattr(file, "name", "uploaded.zip"))).name


def _read_bytes(file) -> bytes:
    if isinstance(file, (str, Path)):
        return Path(file).read_bytes()
    if hasattr(file, "getvalue"):
        return file.getvalue()
    if hasattr(file, "read"):
        try:
            file.seek(0)
        except Exception:
            pass
        data = file.read()
        try:
            file.seek(0)
        except Exception:
            pass
        return data
    raise ZipImageParseError("无法读取ZIP文件内容")


def _safe_parts(path: str) -> tuple[str, ...]:
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    parts = tuple(part for part in pure.parts if part not in {"", "."})

    if not parts:
        return ()
    if pure.is_absolute() or normalized.startswith(("/", "\\")):
        raise ZipImageParseError(f"ZIP内存在绝对路径：{path}")
    if any(part == ".." for part in parts):
        raise ZipImageParseError(f"ZIP内存在路径穿越：{path}")
    if parts[0].endswith(":") or ":" in parts[0]:
        raise ZipImageParseError(f"ZIP内存在异常路径：{path}")
    return parts


def _is_system_path(parts: Iterable[str]) -> bool:
    lower_parts = [part.lower() for part in parts]
    if any(part in SYSTEM_DIR_NAMES for part in lower_parts):
        return True
    return bool(lower_parts and lower_parts[-1] in SYSTEM_FILE_NAMES)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    file_type = (info.external_attr >> 16) & 0o170000
    return file_type == 0o120000


def _validate_info(info: zipfile.ZipInfo, relative_path: str, budget: _ZipBudget) -> tuple[str, ...] | None:
    parts = _safe_parts(info.filename)
    if not parts or _is_system_path(parts):
        return None
    if info.flag_bits & 0x1:
        raise ZipImageParseError(f"暂不支持加密ZIP条目：{relative_path}")
    if _is_symlink(info):
        raise ZipImageParseError(f"暂不支持ZIP内符号链接：{relative_path}")
    if not info.is_dir():
        budget.record_entry(
            info,
            relative_path,
        )
    return parts


def _common_root(infos: list[zipfile.ZipInfo]) -> str | None:
    first_parts = []
    for info in infos:
        try:
            parts = _safe_parts(info.filename)
        except ZipImageParseError:
            continue
        if not parts or _is_system_path(parts):
            continue
        first_parts.append(parts[0])

    unique = set(first_parts)
    if len(unique) == 1:
        return first_parts[0]
    return None


def _join_path(*parts: str) -> str:
    return "/".join(part.strip("/") for part in parts if part)


def _material_group(parts: tuple[str, ...], common_root: str | None) -> str:
    effective = parts
    if common_root and effective and effective[0] == common_root:
        effective = effective[1:]
    if len(effective) >= 2:
        return effective[0]
    return "未明确资料组"


def _read_zip_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo, relative_path: str) -> bytes:
    try:
        return zf.read(info)
    except RuntimeError as exc:
        raise ZipImageParseError(f"读取ZIP条目失败：{relative_path}") from exc


def inspect_zip_images(file) -> ZipImageInventory:
    source_archive = _get_source_name(file)
    archive_bytes = _read_bytes(file)
    budget = _ZipBudget()
    inventory = ZipImageInventory(source_archive=source_archive)

    try:
        with zipfile.ZipFile(BytesIO(archive_bytes)) as zf:
            _collect_zip_images(
                zf,
                inventory,
                budget,
                outer_prefix="",
                depth=0,
                outer_common_root=_common_root(zf.infolist()),
            )
    except zipfile.BadZipFile as exc:
        raise ZipImageParseError(f"ZIP文件损坏或无法识别：{source_archive}") from exc

    inventory.entry_count = budget.entry_count
    inventory.total_uncompressed_bytes = budget.total_uncompressed_bytes
    inventory.inner_zip_count = budget.nested_zip_count

    if not inventory.images:
        unsupported = "; ".join(
            f"{item.relative_path}: {item.reason}"
            for item in inventory.unsupported[:5]
        )
        detail = f"（{unsupported}）" if unsupported else ""
        raise ZipImageParseError(f"ZIP中未发现可解析图片{detail}")

    return inventory


def _collect_zip_images(
    zf: zipfile.ZipFile,
    inventory: ZipImageInventory,
    budget: _ZipBudget,
    outer_prefix: str,
    depth: int,
    outer_common_root: str | None,
) -> None:
    infos = sorted(
        zf.infolist(),
        key=lambda item: item.filename,
    )

    for info in infos:
        relative_path = _join_path(
            outer_prefix,
            info.filename,
        )
        parts = _validate_info(
            info,
            relative_path,
            budget,
        )
        if parts is None or info.is_dir():
            continue

        suffix = Path(parts[-1]).suffix.lower()

        if suffix in IMAGE_EXTENSIONS:
            data = _read_zip_member(
                zf,
                info,
                relative_path,
            )
            outer_parts = _safe_parts(relative_path)
            inventory.images.append(
                ZipImageItem(
                    source_archive=inventory.source_archive,
                    relative_path=relative_path,
                    material_group=_material_group(
                        outer_parts,
                        outer_common_root,
                    ),
                    source_filename=parts[-1],
                    data=data,
                    depth=depth,
                )
            )
            continue

        if suffix in ZIP_EXTENSIONS:
            if depth >= 1:
                inventory.unsupported.append(
                    ZipUnsupportedItem(
                        relative_path=relative_path,
                        reason="暂不支持第三层ZIP",
                    )
                )
                continue

            budget.record_nested_zip(relative_path)
            nested_bytes = _read_zip_member(
                zf,
                info,
                relative_path,
            )
            try:
                with zipfile.ZipFile(BytesIO(nested_bytes)) as nested:
                    _collect_zip_images(
                        nested,
                        inventory,
                        budget,
                        outer_prefix=relative_path,
                        depth=depth + 1,
                        outer_common_root=outer_common_root,
                    )
            except zipfile.BadZipFile:
                inventory.unsupported.append(
                    ZipUnsupportedItem(
                        relative_path=relative_path,
                        reason="内层ZIP损坏或无法识别",
                    )
                )
            continue

        inventory.unsupported.append(
            ZipUnsupportedItem(
                relative_path=relative_path,
                reason=f"暂不支持ZIP内文件类型：{suffix or '无扩展名'}",
            )
        )


def _render_image_material(item: ZipImageItem, recognized_text: str, index: int, total: int) -> str:
    return "\n".join(
        [
            f"【ZIP图片 {index}/{total}】",
            f"【来源压缩包：{item.source_archive}】",
            f"【资料组：{item.material_group}】",
            f"【原始路径：{item.relative_path}】",
            f"【图片文件：{item.source_filename}】",
            "",
            "【图片识别内容】",
            recognized_text.strip(),
        ]
    )


def parse_zip_images(file) -> str:
    inventory = inspect_zip_images(file)
    blocks = []
    failures = []
    total = len(inventory.images)

    for index, item in enumerate(inventory.images, start=1):
        try:
            recognized_text = parse_image(item).strip()
            if not recognized_text:
                raise ValueError("视觉模型未返回有效文本")
            blocks.append(
                _render_image_material(
                    item,
                    recognized_text,
                    index,
                    total,
                )
            )
        except Exception as exc:
            failures.append(
                f"{item.relative_path}: {exc}"
            )

    if failures:
        failure_text = "\n".join(failures[:20])
        raise ZipImageParseError(
            f"ZIP图片资料未完整解析，成功 {len(blocks)}/{total}，失败 {len(failures)}/{total}。\n{failure_text}"
        )

    unsupported = [
        f"{item.relative_path}: {item.reason}"
        for item in inventory.unsupported
    ]
    if unsupported:
        raise ZipImageParseError(
            "ZIP中存在不支持的文件，未进入正式生成：\n"
            + "\n".join(unsupported[:20])
        )

    summary = "\n".join(
        [
            f"【ZIP解析摘要】",
            f"来源压缩包：{inventory.source_archive}",
            f"发现图片数量：{len(inventory.images)}",
            f"内层ZIP数量：{inventory.inner_zip_count}",
            f"累计解压大小：{inventory.total_uncompressed_bytes}",
        ]
    )

    return "\n\n".join(
        [summary, *blocks]
    )

