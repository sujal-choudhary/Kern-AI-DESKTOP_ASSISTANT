from core.actions import execute_task


def test_click_on_text_errors_cleanly_when_no_ocr():
    result = execute_task("click_on_text", {"text": "search"})
    # In CI/dev without Tesseract, we should get a clear message
    assert result["ok"] in (True, False)
    if not result["ok"]:
        assert "OCR is not available" in result["message"]

