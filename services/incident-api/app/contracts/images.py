import base64
import binascii
import warnings
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000


class IncidentImage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    data_url: str = Field(alias="dataUrl", max_length=4 * ((MAX_IMAGE_BYTES + 2) // 3) + 32)

    @field_validator("data_url")
    @classmethod
    def validate_raster(cls, value: str) -> str:
        header, separator, encoded = value.partition(",")
        formats = {"data:image/png;base64": "PNG", "data:image/jpeg;base64": "JPEG"}
        if not separator or header not in formats:
            raise ValueError("Screenshot must be a base64 PNG or JPEG data URL")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("Screenshot contains malformed base64") from error
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            raise ValueError("Screenshot must be nonempty and 2 MB or smaller")
        expected = formats[header]
        signature = b"\x89PNG\r\n\x1a\n" if expected == "PNG" else b"\xff\xd8\xff"
        if not raw.startswith(signature):
            raise ValueError("Screenshot MIME type does not match its signature")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw), formats=[expected]) as image:
                    if image.width * image.height > MAX_IMAGE_PIXELS:
                        raise ValueError("Screenshot exceeds the 16 megapixel limit")
                    if getattr(image, "n_frames", 1) != 1:
                        raise ValueError("Animated screenshots are not supported")
                    image.verify()
                with Image.open(BytesIO(raw), formats=[expected]) as image:
                    image.load()
        except (
            UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning,
        ) as error:
            raise ValueError(
                "Screenshot is malformed, unreadable, or exceeds raster limits"
            ) from error
        return value
