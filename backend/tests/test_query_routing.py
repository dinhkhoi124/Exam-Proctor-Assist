from app.services.query_routing import select_retrieval_query


def test_voice_bypasses_rewrite():
    called = False

    def rewrite(_message, _image):
        nonlocal called
        called = True
        return "rewritten"

    result = select_retrieval_query(
        input_type="voice",
        query_text="raw or corrected voice text",
        message="voice text",
        image_description="",
        rewrite=rewrite,
    )
    assert result == "raw or corrected voice text"
    assert called is False


def test_text_preserves_existing_rewrite():
    result = select_retrieval_query(
        input_type="text",
        query_text="typed text",
        message="typed text",
        image_description="ocr",
        rewrite=lambda message, image: f"{message}|{image}",
    )
    assert result == "typed text|ocr"
