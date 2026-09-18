from __future__ import annotations

import zipfile
from io import BytesIO

import pytest
from PIL import Image

from parser import zip_image_parser
from parser.parser_factory import parse_file
from parser.zip_image_parser import ZipImageParseError, inspect_zip_images, parse_zip_images


class NamedBytesIO(BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name

    def getvalue(self) -> bytes:
        return super().getvalue()


def _image_bytes(fmt="JPEG", color=(120, 40, 80)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (80, 40), color).save(buffer, format=fmt)
    return buffer.getvalue()


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def _named_zip(entries: dict[str, bytes], name="materials.zip"):
    return NamedBytesIO(_zip_bytes(entries), name)


def test_inspect_zip_images_collects_outer_and_inner_images():
    inner = _zip_bytes(
        {
            "参数牌.jpg": _image_bytes(color=(1, 2, 3)),
            "折页反.jpg": _image_bytes(color=(3, 2, 1)),
        }
    )
    file = _named_zip(
        {
            "参数表/哈弗H6L/哈弗-H6L.zip": inner,
            "参数表/二代哈弗H9/参数牌.jpg": _image_bytes(),
            "__MACOSX/._junk": b"ignored",
            "参数表/.DS_Store": b"ignored",
        },
        "参数表.zip",
    )

    inventory = inspect_zip_images(file)

    assert inventory.image_count == 3
    assert inventory.inner_zip_count == 1
    paths = [item.relative_path for item in inventory.images]
    assert "参数表/哈弗H6L/哈弗-H6L.zip/参数牌.jpg" in paths
    assert "参数表/哈弗H6L/哈弗-H6L.zip/折页反.jpg" in paths
    assert "参数表/二代哈弗H9/参数牌.jpg" in paths
    groups = {item.relative_path: item.material_group for item in inventory.images}
    assert groups["参数表/哈弗H6L/哈弗-H6L.zip/参数牌.jpg"] == "哈弗H6L"
    assert groups["参数表/二代哈弗H9/参数牌.jpg"] == "二代哈弗H9"


def test_parse_zip_images_keeps_source_metadata(monkeypatch):
    file = _named_zip(
        {
            "参数表/哈弗H6L/参数牌.jpg": _image_bytes(),
        },
        "参数表.zip",
    )

    def fake_parse_image(image):
        assert image.name == "参数牌.jpg"
        assert image.getvalue()
        return "识别到哈弗H6L参数。"

    monkeypatch.setattr(zip_image_parser, "parse_image", fake_parse_image)

    material = parse_zip_images(file)

    assert "【来源压缩包：参数表.zip】" in material
    assert "【资料组：哈弗H6L】" in material
    assert "【原始路径：参数表/哈弗H6L/参数牌.jpg】" in material
    assert "识别到哈弗H6L参数。" in material


def test_parse_file_routes_zip(monkeypatch):
    file = _named_zip(
        {
            "参数表/哈弗H6L/参数牌.jpg": _image_bytes(),
        }
    )

    monkeypatch.setattr(
        "parser.parser_factory.parse_zip_images",
        lambda uploaded: "ZIP Material",
    )

    assert parse_file(file) == "ZIP Material"


def test_zip_rejects_path_traversal():
    file = _named_zip(
        {
            "../evil.jpg": _image_bytes(),
        }
    )

    with pytest.raises(ZipImageParseError, match="路径穿越"):
        inspect_zip_images(file)


def test_zip_rejects_absolute_path():
    file = _named_zip(
        {
            "/evil.jpg": _image_bytes(),
        }
    )

    with pytest.raises(ZipImageParseError, match="绝对路径"):
        inspect_zip_images(file)


def test_zip_reports_third_level_zip_as_unsupported():
    third = _zip_bytes({"参数牌.jpg": _image_bytes()})
    inner = _zip_bytes({"third.zip": third})
    file = _named_zip(
        {
            "参数表/哈弗H6L/inner.zip": inner,
            "参数表/哈弗H6L/参数牌.jpg": _image_bytes(),
        }
    )

    inventory = inspect_zip_images(file)

    assert inventory.image_count == 1
    assert inventory.unsupported[0].reason == "暂不支持第三层ZIP"


def test_parse_zip_images_fails_on_unsupported_files(monkeypatch):
    file = _named_zip(
        {
            "参数表/哈弗H6L/参数牌.jpg": _image_bytes(),
            "参数表/哈弗H6L/readme.txt": b"not supported",
        }
    )
    monkeypatch.setattr(zip_image_parser, "parse_image", lambda image: "ok")

    with pytest.raises(ZipImageParseError, match="不支持的文件"):
        parse_zip_images(file)


def test_empty_zip_fails():
    file = _named_zip({})

    with pytest.raises(ZipImageParseError, match="未发现可解析图片"):
        inspect_zip_images(file)


def test_no_image_zip_fails_with_unsupported_detail():
    file = _named_zip({"参数表/说明.txt": b"hello"})

    with pytest.raises(ZipImageParseError, match="暂不支持ZIP内文件类型"):
        inspect_zip_images(file)


def test_damaged_zip_fails():
    file = NamedBytesIO(b"not a zip", "bad.zip")

    with pytest.raises(ZipImageParseError, match="损坏"):
        inspect_zip_images(file)


def test_encrypted_zip_entry_is_rejected():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("参数表/哈弗H6L/参数牌.jpg", _image_bytes())

    data = bytearray(buffer.getvalue())
    for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        start = 0
        while True:
            index = data.find(signature, start)
            if index < 0:
                break
            flag_index = index + flag_offset
            flag = int.from_bytes(data[flag_index:flag_index + 2], "little")
            data[flag_index:flag_index + 2] = (flag | 0x1).to_bytes(2, "little")
            start = index + 4

    file = NamedBytesIO(bytes(data), "encrypted.zip")

    with pytest.raises(ZipImageParseError, match="加密"):
        inspect_zip_images(file)
