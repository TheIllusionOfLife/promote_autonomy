"""Image generation service."""

from typing import Optional, Protocol
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from promote_autonomy_shared.schemas import BrandStyle, ImageTaskConfig

from app.core.config import get_settings



class ImageService(Protocol):
    """Protocol for image generation services."""

    async def generate_image(
        self, config: ImageTaskConfig, brand_style: Optional[BrandStyle] = None
    ) -> bytes:
        """Generate image from prompt.

        Args:
            config: Image generation configuration
            brand_style: Brand style guide (optional)

        Returns:
            Image bytes (PNG format)
        """
        ...


class MockImageService:
    """Mock image generation for testing."""

    async def generate_image(
        self, config: ImageTaskConfig, brand_style: Optional[BrandStyle] = None
    ) -> bytes:
        """Generate placeholder image with text overlay."""
        # Parse size (e.g., "1024x1024")
        width, height = map(int, config.size.split("x"))

        # Use brand primary color if available, otherwise default
        bg_color = (100, 149, 237)  # Default: Cornflower blue
        if brand_style and brand_style.colors:
            # Find primary color, fallback to first if no primary specified
            primary_color = next(
                (c for c in brand_style.colors if c.usage == "primary"),
                brand_style.colors[0]
            )
            # Convert hex to RGB
            hex_code = primary_color.hex_code
            bg_color = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

        # Create image with solid color background
        img = Image.new("RGB", (width, height), color=bg_color)

        # Add text overlay
        draw = ImageDraw.Draw(img)

        # Try to use a nice font, fall back to default if unavailable
        # Check multiple paths for cross-platform support (Linux, macOS, Windows)
        font = None
        for font_path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux (Cloud Run)
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "C:\\Windows\\Fonts\\arial.ttf",  # Windows
        ]:
            try:
                font = ImageFont.truetype(font_path, size=40)
                break
            except (OSError, IOError):
                continue

        if font is None:
            font = ImageFont.load_default()

        # Wrap prompt text
        prompt_text = config.prompt[:100] + "..." if len(config.prompt) > 100 else config.prompt
        lines = []
        words = prompt_text.split()
        current_line = []

        for word in words:
            current_line.append(word)
            test_line = " ".join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > width - 40:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        # Center text vertically
        line_height = 50
        total_height = len(lines) * line_height
        y = (height - total_height) // 2

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y), line, fill="white", font=font)
            y += line_height

        # Add "MOCK IMAGE" watermark
        watermark_font = None
        for font_path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux (Cloud Run)
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "C:\\Windows\\Fonts\\arial.ttf",  # Windows
        ]:
            try:
                watermark_font = ImageFont.truetype(font_path, size=20)
                break
            except (OSError, IOError):
                continue

        if watermark_font is None:
            watermark_font = font

        watermark = "MOCK IMAGE"
        bbox = draw.textbbox((0, 0), watermark, font=watermark_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((width - text_width) // 2, height - 40),
            watermark,
            fill=(255, 255, 255),  # RGB only (no alpha channel on RGB image)
            font=watermark_font,
        )

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()


class RealImageService:
    """Real image generation using Vertex AI Imagen."""

    def __init__(self):
        """Initialize Vertex AI for image generation."""
        import vertexai
        from vertexai.preview.vision_models import ImageGenerationModel

        settings = get_settings()
        vertexai.init(project=settings.PROJECT_ID, location=settings.LOCATION)
        self.model = ImageGenerationModel.from_pretrained(settings.IMAGEN_MODEL)

    async def generate_image(
        self, config: ImageTaskConfig, brand_style: Optional[BrandStyle] = None
    ) -> bytes:
        """Generate image using Imagen."""
        # Parse size
        width, height = map(int, config.size.split("x"))

        # Use explicit aspect_ratio if provided, otherwise calculate from size
        if config.aspect_ratio:
            imagen_aspect_ratio = config.aspect_ratio
        else:
            # Determine aspect ratio for Imagen
            # Imagen supports: 1:1, 9:16, 16:9, 4:3, 3:4
            aspect_ratio = width / height
            if aspect_ratio > 1.5:
                imagen_aspect_ratio = "16:9"
            elif aspect_ratio < 0.7:
                imagen_aspect_ratio = "9:16"
            elif aspect_ratio > 1.2:
                imagen_aspect_ratio = "4:3"
            elif aspect_ratio < 0.85:
                imagen_aspect_ratio = "3:4"
            else:
                imagen_aspect_ratio = "1:1"

        # Enhance prompt with brand colors if provided
        enhanced_prompt = config.prompt
        if brand_style and brand_style.colors:
            # Find primary color, fallback to first if no primary specified
            primary_color = next(
                (c for c in brand_style.colors if c.usage == "primary"),
                brand_style.colors[0]
            )
            # Include primary color prominently, then other colors
            other_colors = [c for c in brand_style.colors[:3] if c != primary_color]
            color_desc = f"Primary color: {primary_color.name} (#{primary_color.hex_code})"
            if other_colors:
                other_desc = ", ".join([f"{c.name} (#{c.hex_code})" for c in other_colors])
                color_desc += f". Additional colors: {other_desc}"
            enhanced_prompt = f"{config.prompt}. {color_desc}."

        # Generate image
        response = self.model.generate_images(
            prompt=enhanced_prompt,
            number_of_images=1,
            aspect_ratio=imagen_aspect_ratio,
        )

        # Check if response has images
        if not response.images:
            raise RuntimeError("Vertex AI Imagen returned no images")

        # Get first image
        vertex_image = response.images[0]
        image_bytes = vertex_image._image_bytes  # Access internal image bytes property

        # Load image to check actual size
        pil_image = Image.open(BytesIO(image_bytes))
        pil_image.load()

        # Resize to exact requested dimensions if needed
        if pil_image.size != (width, height):
            pil_image = pil_image.resize((width, height), Image.Resampling.LANCZOS)

        # Apply file size compression if max_file_size_mb is specified
        if config.max_file_size_mb:
            image_bytes = self._compress_to_max_size(pil_image, config.max_file_size_mb)
        else:
            buffer = BytesIO()
            pil_image.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()

        return image_bytes

    def _compress_to_max_size(self, image: Image.Image, max_size_mb: float) -> bytes:
        """Compress image to meet file size constraint.

        Args:
            image: PIL Image to compress
            max_size_mb: Maximum file size in megabytes

        Returns:
            Compressed image bytes in JPEG format (better compression than PNG)
        """
        max_size_bytes = int(max_size_mb * 1024 * 1024)

        # Convert RGBA/LA/P modes to RGB for JPEG compatibility
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Start with high quality JPEG
        quality = 95
        buffer = BytesIO()

        while quality > 10:
            buffer.seek(0)
            buffer.truncate()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            size = buffer.tell()

            if size <= max_size_bytes:
                return buffer.getvalue()

            # Reduce quality by 10 each iteration
            quality -= 10

        # If still too large, return at minimum quality
        buffer.seek(0)
        buffer.truncate()
        image.save(buffer, format="JPEG", quality=10, optimize=True)
        return buffer.getvalue()


# Service instance management
_mock_image_service: MockImageService | None = None
_real_image_service: RealImageService | None = None


def get_image_service() -> ImageService:
    """Get image service instance (singleton)."""
    global _mock_image_service, _real_image_service

    settings = get_settings()

    if settings.USE_MOCK_IMAGEN:
        if _mock_image_service is None:
            _mock_image_service = MockImageService()
        return _mock_image_service
    else:
        if _real_image_service is None:
            _real_image_service = RealImageService()
        return _real_image_service
