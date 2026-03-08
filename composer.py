"""
Image composition module for Telegram Story userbot.
Handles downloading, resizing, caption overlay, and gradient effects.
"""

import io
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests

logger = logging.getLogger(__name__)


class ImageComposer:
    """Composes images for Telegram Stories with captions and gradient overlays."""

    def __init__(
        self,
        story_width: int = 1080,
        story_height: int = 1920,
        caption_font_size: int = 48,
        caption_text_color: str = "#FFFFFF",
        gradient_opacity_start: int = 170,
        gradient_height_ratio: float = 0.35,
    ):
        self.story_width = story_width
        self.story_height = story_height
        self.caption_font_size = caption_font_size
        self.caption_text_color = caption_text_color
        self.gradient_opacity_start = gradient_opacity_start
        self.gradient_height_ratio = gradient_height_ratio
        self.font = self._load_font()

    def _load_font(self) -> ImageFont.FreeTypeFont:
        """Load a bold sans-serif font. Tries multiple options for compatibility."""
        font_options = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
            "/usr/share/fonts/truetype/arial/arialbd.ttf",
            "/System/Library/Fonts/Helvetica.ttc",  # macOS fallback
            "arialbd.ttf",  # Windows fallback
            "DejaVuSans-Bold.ttf",
        ]

        for font_path in font_options:
            try:
                font = ImageFont.truetype(font_path, self.caption_font_size)
                logger.info(f"Loaded font: {font_path}")
                return font
            except (OSError, IOError):
                continue

        # Fallback to default font
        logger.warning("No bold font found, using default font")
        return ImageFont.load_default()

    def download_image(self, url: str) -> Image.Image:
        """Download an image from a URL and return a PIL Image."""
        logger.info(f"Downloading image from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        logger.info(f"Downloaded image: {image.size}, mode: {image.mode}")
        return image

    def resize_and_crop(self, image: Image.Image) -> Image.Image:
        """
        Resize and center-crop image to story dimensions (1080x1920).
        Maintains aspect ratio and crops to center.
        """
        # Convert to RGB if necessary
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        img_width, img_height = image.size
        target_ratio = self.story_width / self.story_height
        img_ratio = img_width / img_height

        if img_ratio > target_ratio:
            # Image is wider than target, crop width
            new_width = int(img_height * target_ratio)
            left = (img_width - new_width) // 2
            image = image.crop((left, 0, left + new_width, img_height))
        elif img_ratio < target_ratio:
            # Image is taller than target, crop height
            new_height = int(img_width / target_ratio)
            top = (img_height - new_height) // 2
            image = image.crop((0, top, img_width, top + new_height))

        # Resize to exact dimensions
        image = image.resize((self.story_width, self.story_height), Image.Resampling.LANCZOS)
        logger.info(f"Resized image to: {image.size}")
        return image

    def _create_gradient_bar(self, width: int, height: int) -> Image.Image:
        """
        Create a soft gradient bar from transparent to dark.
        Gradient fades from bottom (dark) to top (transparent).
        """
        gradient = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(gradient)

        # Create gradient line by line
        for y in range(height):
            # Calculate alpha: 0 at top, gradient_opacity_start at bottom
            alpha = int((y / height) * self.gradient_opacity_start)
            draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

        # Apply slight blur for soft edge
        gradient = gradient.filter(ImageFilter.GaussianBlur(radius=8))
        return gradient

    def _draw_text_with_shadow(
        self,
        draw: ImageDraw.Draw,
        text: str,
        x: int,
        y: int,
        font: ImageFont.FreeTypeFont,
        text_color: str,
        shadow_color: str = "#000000",
        shadow_offset: int = 3,
        shadow_blur: int = 4,
    ) -> None:
        """Draw text with a drop shadow for readability."""
        # Parse colors
        text_rgb = self._hex_to_rgb(text_color)
        shadow_rgb = self._hex_to_rgb(shadow_color)

        # Draw shadow (multiple layers for blur effect)
        for offset in range(shadow_blur, 0, -1):
            alpha = int(255 * (1 - offset / (shadow_blur + 2)))
            shadow_rgba = (*shadow_rgb, alpha)
            shadow_x = x + shadow_offset + offset // 2
            shadow_y = y + shadow_offset + offset // 2
            draw.text((shadow_x, shadow_y), text, font=font, fill=shadow_rgba)

        # Draw main text
        draw.text((x, y), text, font=font, fill=text_rgb)

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            text_width = bbox[2] - bbox[0] if bbox else 0

            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, add it anyway
                    lines.append(word)
                    current_line = []

        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [text]

    def compose(self, image: Image.Image, caption: str) -> bytes:
        """
        Compose the final story image with gradient and caption.
        Returns JPEG bytes ready for upload.
        """
        # Resize and crop to story dimensions
        composed = self.resize_and_crop(image)

        # Create gradient overlay
        gradient_height = int(self.story_height * self.gradient_height_ratio)
        gradient = self._create_gradient_bar(self.story_width, gradient_height)

        # Paste gradient at bottom
        composed_rgba = composed.convert("RGBA")
        composed_rgba.paste(gradient, (0, self.story_height - gradient_height), gradient)

        # Prepare for text drawing
        draw = ImageDraw.Draw(composed_rgba)

        # Wrap caption text
        max_text_width = self.story_width - 80  # 40px padding on each side
        lines = self._wrap_text(caption, self.font, max_text_width)

        # Calculate text positioning (centered, in bottom 25%)
        line_height = self.caption_font_size + 10
        total_text_height = len(lines) * line_height
        text_area_top = self.story_height - gradient_height + (gradient_height - total_text_height) // 2

        # Draw each line
        for i, line in enumerate(lines):
            bbox = self.font.getbbox(line)
            text_width = bbox[2] - bbox[0] if bbox else 0
            x = (self.story_width - text_width) // 2
            y = text_area_top + i * line_height

            self._draw_text_with_shadow(
                draw, line, x, y, self.font,
                self.caption_text_color,
                shadow_color="#000000",
                shadow_offset=3,
                shadow_blur=4,
            )

        # Convert back to RGB and save as JPEG
        final = composed_rgba.convert("RGB")
        output = io.BytesIO()
        final.save(output, format="JPEG", quality=95, optimize=True)
        output.seek(0)

        logger.info(f"Composed story image with caption: {caption[:50]}...")
        return output.getvalue()

    def process_image_from_url(self, url: str, caption: str) -> bytes:
        """Download and process an image from URL."""
        image = self.download_image(url)
        return self.compose(image, caption)

    def process_image_from_bytes(self, image_bytes: bytes, caption: str) -> bytes:
        """Process an image from bytes."""
        image = Image.open(io.BytesIO(image_bytes))
        return self.compose(image, caption)
