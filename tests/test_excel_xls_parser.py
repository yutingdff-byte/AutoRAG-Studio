from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pytest
import xlwt
from openpyxl import Workbook

from parser.excel_parser import parse_excel
from parser.parser_factory import parse_file


class NamedBytesIO(BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name


def _xls_bytes(sheets: dict[str, list[list[object]]]) -> bytes:
    workbook = xlwt.Workbook()
    date_style = xlwt.easyxf(num_format_str="YYYY-MM-DD")
    for sheet_name, rows in sheets.items():
        worksheet = workbook.add_sheet(sheet_name)
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                if isinstance(value, datetime):
                    worksheet.write(row_index, col_index, value, date_style)
                else:
                    worksheet.write(row_index, col_index, value)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _xlsx_bytes(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parse_legacy_xls_row_oriented_table():
    data = _xls_bytes(
        {
            "价格表": [
                ["车型", "版本", "价格", "上市日期"],
                ["哈弗H6", "经典版", 99900, datetime(2026, 6, 1)],
                ["哈弗H6", "Pro", "", ""],
            ]
        }
    )

    parsed = parse_excel(NamedBytesIO(data, "legacy.xls"))

    assert "【文件来源：legacy.xls】" in parsed
    assert "【Sheet:价格表】" in parsed
    assert "字段：车型 | 版本 | 价格 | 上市日期" in parsed
    assert "车型: 哈弗H6" in parsed
    assert "版本: 经典版" in parsed
    assert "价格: 99900" in parsed
    assert "上市日期: 2026-06-01" in parsed


def test_parse_legacy_xls_multiple_sheets():
    data = _xls_bytes(
        {
            "SheetA": [["车型", "价格"], ["A车型", 100000]],
            "SheetB": [["车型", "价格"], ["B车型", 200000]],
        }
    )

    parsed = parse_file(NamedBytesIO(data, "multi.xls"))

    assert "【Sheet:SheetA】" in parsed
    assert "车型: A车型" in parsed
    assert "【Sheet:SheetB】" in parsed
    assert "车型: B车型" in parsed
    assert "价格: 200000" in parsed


def test_parse_xlsx_still_uses_existing_path():
    data = _xlsx_bytes(
        [
            ["车型", "价格"],
            ["A车型", "10万"],
        ]
    )

    parsed = parse_excel(data)

    assert "字段：车型 | 价格" in parsed
    assert "车型: A车型" in parsed
    assert "价格: 10万" in parsed


def test_fake_xls_reports_clear_error():
    fake_file = NamedBytesIO(b"not a real xls workbook", "broken.xls")

    with pytest.raises(RuntimeError, match="Excel解析失败"):
        parse_excel(fake_file)

