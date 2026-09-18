from io import BytesIO

from PIL import Image

from parser import image_parser


def test_large_image_is_preprocessed_under_model_limit(monkeypatch):
    monkeypatch.setattr(image_parser, "MAX_IMAGE_SIZE_BYTES", 500_000)

    image = Image.effect_noise((1200, 1200), 100).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    original = buffer.getvalue()
    assert len(original) > image_parser.MAX_IMAGE_SIZE_BYTES

    prepared, mime_type = image_parser._prepare_image_bytes_for_model(
        original,
        "large.jpg",
    )

    assert len(prepared) <= image_parser.MAX_IMAGE_SIZE_BYTES
    assert mime_type == "image/jpeg"
