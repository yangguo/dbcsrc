"""Offline tests for the text-layer gate and concurrent page OCR."""

import sys
import types

import doc2text


def test_short_chinese_text_is_not_a_text_layer():
    assert doc2text.text_layer_ok("第1页") is False


def test_whitespace_only_is_not_a_text_layer():
    assert doc2text.text_layer_ok("  \n\t  ") is False


def test_page_number_only_is_not_a_text_layer():
    assert doc2text.text_layer_ok("12 / 30") is False


def test_long_chinese_text_is_a_text_layer():
    assert doc2text.text_layer_ok("本局决定对当事人处以罚款三十万元并责令改正。" * 2)


def test_none_and_empty_are_not_a_text_layer():
    assert doc2text.text_layer_ok(None) is False
    assert doc2text.text_layer_ok("") is False


class FakePixmap:
    def __init__(self, page_number):
        self.page_number = page_number

    def save(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"page {self.page_number}")


class FakePage:
    def __init__(self, page_number):
        self.page_number = page_number

    def get_pixmap(self, matrix=None):
        return FakePixmap(self.page_number)


class FakeDocument:
    def __init__(self, page_count):
        self.page_count = page_count
        self.closed = False

    def __len__(self):
        return self.page_count

    def load_page(self, index):
        return FakePage(index + 1)

    def close(self):
        self.closed = True


def install_fake_fitz(monkeypatch, page_count):
    fake_module = types.SimpleNamespace(
        Matrix=lambda x, y: (x, y),
        open=lambda _path: FakeDocument(page_count),
    )
    monkeypatch.setitem(sys.modules, "fitz", fake_module)


def test_pdfurl2ocr_keeps_page_order(monkeypatch, tmp_path):
    install_fake_fitz(monkeypatch, 3)
    calls = []

    def fake_ocr(path):
        calls.append(path)
        return f"text-{doc2text.os.path.basename(path).split('_')[1].split('.')[0]}"

    monkeypatch.setattr(doc2text, "llm_ocr_text", fake_ocr)

    result = doc2text.pdfurl2ocr("fake.pdf", str(tmp_path))

    assert result.split() == ["text-1", "text-2", "text-3"]
    assert len(calls) == 3


def test_pdfurl2ocr_removes_page_images(monkeypatch, tmp_path):
    install_fake_fitz(monkeypatch, 2)
    monkeypatch.setattr(doc2text, "llm_ocr_text", lambda _path: "文字")

    doc2text.pdfurl2ocr("fake.pdf", str(tmp_path))

    assert list(tmp_path.glob("*.png")) == []
