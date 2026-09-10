# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11"]
# ///
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 800
SUPERSAMPLE = 3
CX = 400
CY = 330
# Vorschauen separat ablegen, damit die fertigen Produktfotos erhalten bleiben.
OUT_DIR = Path(__file__).resolve().parents[1] / "output" / "placeholders"
FONT_DIR = Path(r"C:\Windows\Fonts")

Rgb = tuple[int, int, int]
Rgba = tuple[int, int, int, int]
Box = tuple[float, float, float, float]
Point = tuple[float, float]


@dataclass(frozen=True)
class Placeholder:
    slug: str
    name: str
    category: str
    gradient: tuple[str, str]
    fill: str
    detail: str
    shape: str


PRODUCTS: tuple[Placeholder, ...] = (
    Placeholder(
        "nordlicht-kopfhoerer",
        "Nordlicht",
        "Over-Ear-Kopfhörer",
        ("#0f172a", "#475569"),
        "#e2e8f0",
        "#1e293b",
        "headphones",
    ),
    Placeholder(
        "klangkugel-lautsprecher",
        "Klangkugel",
        "Bluetooth-Lautsprecher",
        ("#0f766e", "#5eead4"),
        "#f0fdfa",
        "#115e59",
        "speaker",
    ),
    Placeholder(
        "tastwerk-tastatur",
        "Tastwerk 75",
        "Mechanische Tastatur",
        ("#312e81", "#818cf8"),
        "#e0e7ff",
        "#3730a3",
        "keyboard",
    ),
    Placeholder(
        "mahlwerk-kaffeemuehle",
        "Mahlwerk",
        "Kaffeemühle",
        ("#78350f", "#f59e0b"),
        "#fef3c7",
        "#92400e",
        "grinder",
    ),
    Placeholder(
        "morgenrot-tasse",
        "Morgenrot",
        "Keramiktasse",
        ("#9f1239", "#fb7185"),
        "#ffe4e6",
        "#be123c",
        "mug",
    ),
    Placeholder(
        "lumo-schreibtischlampe",
        "Lumo",
        "Schreibtischlampe",
        ("#854d0e", "#facc15"),
        "#fefce8",
        "#a16207",
        "lamp",
    ),
    Placeholder(
        "linie-notizbuch",
        "Linie",
        "Notizbuch-Set",
        ("#1e3a8a", "#60a5fa"),
        "#dbeafe",
        "#1d4ed8",
        "notebook",
    ),
    Placeholder(
        "wanderer-rucksack",
        "Wanderer",
        "Lederrucksack",
        ("#7c2d12", "#ea580c"),
        "#ffedd5",
        "#9a3412",
        "backpack",
    ),
    Placeholder(
        "alltag-tragetasche",
        "Alltag",
        "Canvas-Tasche",
        ("#365314", "#a3e635"),
        "#f7fee7",
        "#4d7c0f",
        "tote",
    ),
    Placeholder(
        "quell-trinkflasche",
        "Quell",
        "Trinkflasche",
        ("#075985", "#38bdf8"),
        "#e0f2fe",
        "#0369a1",
        "bottle",
    ),
    Placeholder(
        "glut-thermoskanne",
        "Glut",
        "Thermoskanne",
        ("#7f1d1d", "#f87171"),
        "#fee2e2",
        "#b91c1c",
        "thermos",
    ),
    Placeholder(
        "fjord-muetze",
        "Fjord",
        "Wollmütze",
        ("#4c1d95", "#a78bfa"),
        "#ede9fe",
        "#6d28d9",
        "beanie",
    ),
)


def hex_to_rgb(value: str) -> Rgb:
    digits = value.lstrip("#")
    return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))


def opaque(value: str) -> Rgba:
    return (*hex_to_rgb(value), 255)


class Pen:
    def __init__(self, draw: ImageDraw.ImageDraw, scale: int) -> None:
        self._draw = draw
        self._scale = scale

    def rrect(self, box: Box, radius: float, fill: Rgba) -> None:
        self._draw.rounded_rectangle(
            self._box(box), radius=radius * self._scale, fill=fill
        )

    def rect(self, box: Box, fill: Rgba) -> None:
        self._draw.rectangle(self._box(box), fill=fill)

    def ellipse(
        self,
        box: Box,
        fill: Rgba | None = None,
        outline: Rgba | None = None,
        width: int = 1,
    ) -> None:
        self._draw.ellipse(
            self._box(box), fill=fill, outline=outline, width=width * self._scale
        )

    def arc(self, box: Box, start: int, end: int, fill: Rgba, width: int) -> None:
        self._draw.arc(self._box(box), start, end, fill=fill, width=width * self._scale)

    def pieslice(self, box: Box, start: int, end: int, fill: Rgba) -> None:
        self._draw.pieslice(self._box(box), start, end, fill=fill)

    def line(self, points: list[Point], fill: Rgba, width: int) -> None:
        self._draw.line(
            self._points(points), fill=fill, width=width * self._scale, joint="curve"
        )

    def polygon(self, points: list[Point], fill: Rgba) -> None:
        self._draw.polygon(self._points(points), fill=fill)

    def _box(self, box: Box) -> Box:
        x0, y0, x1, y1 = box
        return (x0 * self._scale, y0 * self._scale, x1 * self._scale, y1 * self._scale)

    def _points(self, points: list[Point]) -> list[Point]:
        return [(x * self._scale, y * self._scale) for x, y in points]


Shape = Callable[[Pen, Rgba, Rgba], None]


class Silhouettes:
    @staticmethod
    def headphones(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.arc((CX - 190, CY - 190, CX + 190, CY + 190), 195, 345, fill=fill, width=36)
        for sx in (-1, 1):
            x = CX + sx * 170
            pen.rrect((x - 58, CY - 40, x + 58, CY + 120), 32, fill)
            pen.rrect((x - 34, CY - 14, x + 34, CY + 96), 22, detail)

    @staticmethod
    def speaker(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.ellipse((CX - 200, CY - 200, CX + 200, CY + 200), fill=fill)
        pen.ellipse((CX - 160, CY - 160, CX + 160, CY + 160), outline=detail, width=10)
        pen.ellipse((CX - 120, CY - 120, CX + 120, CY + 120), outline=detail, width=6)
        pen.ellipse((CX - 70, CY - 70, CX + 70, CY + 70), fill=detail)
        pen.ellipse((CX - 30, CY - 30, CX + 30, CY + 30), fill=fill)

    @staticmethod
    def keyboard(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.rrect((CX - 270, CY - 120, CX + 270, CY + 120), 30, fill)
        key, gap, cols, rows = 34, 8, 12, 4
        width = cols * key + (cols - 1) * gap
        x0, y0 = CX - width / 2, CY - 90
        for row in range(rows):
            for col in range(cols):
                x, y = x0 + col * (key + gap), y0 + row * (key + gap)
                if row == rows - 1 and 3 <= col <= 8:
                    if col == 3:
                        pen.rrect(
                            (x, y, x0 + 8 * (key + gap) + key, y + key), 8, detail
                        )
                    continue
                pen.rrect((x, y, x + key, y + key), 8, detail)

    @staticmethod
    def grinder(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.polygon(
            [
                (CX - 110, CY - 200),
                (CX + 110, CY - 200),
                (CX + 75, CY - 60),
                (CX - 75, CY - 60),
            ],
            fill,
        )
        pen.ellipse((CX - 110, CY - 222, CX + 110, CY - 178), fill=detail)
        pen.rrect((CX - 105, CY - 60, CX + 105, CY + 200), 34, fill)
        pen.rrect((CX - 70, CY + 50, CX + 70, CY + 165), 18, detail)
        pen.ellipse((CX - 24, CY - 30, CX + 24, CY + 18), fill=detail)

    @staticmethod
    def mug(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.arc((CX + 40, CY - 70, CX + 200, CY + 90), 270, 90, fill=fill, width=38)
        pen.rrect((CX - 150, CY - 120, CX + 90, CY + 160), 34, fill)
        pen.rrect((CX - 150, CY - 120, CX + 90, CY - 78), 16, detail)
        for index, x in enumerate((CX - 100, CX - 40, CX + 20)):
            dy = (index % 2) * 12
            pen.line(
                [
                    (x, CY - 150 - dy),
                    (x + 9, CY - 175 - dy),
                    (x - 9, CY - 200 - dy),
                    (x, CY - 225 - dy),
                ],
                fill,
                10,
            )

    @staticmethod
    def lamp(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.polygon(
            [
                (CX - 215, CY - 100),
                (CX - 25, CY - 100),
                (CX + 40, CY + 150),
                (CX - 280, CY + 150),
            ],
            (255, 250, 200, 70),
        )
        pen.ellipse((CX - 150, CY + 150, CX + 150, CY + 205), fill=fill)
        pen.line([(CX + 20, CY + 175), (CX + 70, CY - 40)], fill, 20)
        pen.line([(CX + 70, CY - 40), (CX - 120, CY - 190)], fill, 20)
        pen.ellipse((CX + 50, CY - 60, CX + 90, CY - 20), fill=detail)
        pen.polygon(
            [
                (CX - 170, CY - 195),
                (CX - 70, CY - 195),
                (CX - 25, CY - 100),
                (CX - 215, CY - 100),
            ],
            fill,
        )

    @staticmethod
    def notebook(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.rrect((CX - 150, CY - 200, CX - 60, CY + 200), 24, detail)
        pen.rrect((CX - 110, CY - 200, CX + 150, CY + 200), 24, fill)
        for index in range(5):
            y = CY - 120 + index * 60
            pen.rrect((CX - 60, y, CX + 100, y + 10), 5, detail)
        pen.rect((CX + 112, CY - 200, CX + 128, CY + 200), detail)

    @staticmethod
    def backpack(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.arc((CX - 70, CY - 230, CX + 70, CY - 110), 180, 360, fill=detail, width=24)
        pen.rrect((CX - 170, CY - 160, CX + 170, CY + 200), 70, fill)
        pen.rrect((CX - 120, CY + 30, CX + 120, CY + 170), 34, detail)
        pen.rrect((CX - 60, CY - 40, CX + 60, CY - 10), 12, detail)

    @staticmethod
    def tote(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        for sx in (-1, 1):
            x = CX + sx * 70
            pen.arc((x - 70, CY - 230, x + 70, CY - 30), 180, 360, fill=fill, width=22)
        pen.polygon(
            [
                (CX - 190, CY - 90),
                (CX + 190, CY - 90),
                (CX + 150, CY + 210),
                (CX - 150, CY + 210),
            ],
            fill,
        )
        pen.polygon(
            [
                (CX - 190, CY - 90),
                (CX + 190, CY - 90),
                (CX + 183, CY - 40),
                (CX - 183, CY - 40),
            ],
            detail,
        )
        pen.rrect((CX - 80, CY + 20, CX + 80, CY + 130), 14, detail)

    @staticmethod
    def bottle(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.rrect((CX - 64, CY - 235, CX + 64, CY - 165), 18, detail)
        pen.rect((CX - 46, CY - 175, CX + 46, CY - 110), fill)
        pen.rrect((CX - 90, CY - 130, CX + 90, CY + 220), 54, fill)
        pen.rect((CX - 90, CY - 10, CX + 90, CY + 70), detail)

    @staticmethod
    def thermos(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.arc((CX + 60, CY - 60, CX + 170, CY + 90), 270, 90, fill=detail, width=22)
        pen.rrect((CX - 80, CY - 235, CX + 80, CY - 140), 22, detail)
        pen.rrect((CX - 100, CY - 150, CX + 100, CY + 220), 46, fill)
        pen.rect((CX - 100, CY - 30, CX + 100, CY + 10), detail)

    @staticmethod
    def beanie(pen: Pen, fill: Rgba, detail: Rgba) -> None:
        pen.ellipse((CX - 48, CY - 250, CX + 48, CY - 154), fill=detail)
        pen.pieslice((CX - 180, CY - 190, CX + 180, CY + 170), 180, 360, fill=fill)
        pen.rrect((CX - 195, CY - 30, CX + 195, CY + 100), 34, detail)
        for index in range(-4, 5):
            x = CX + index * 40
            pen.rect((x - 6, CY - 12, x + 6, CY + 82), fill)

    @classmethod
    def registry(cls) -> dict[str, Shape]:
        return {
            "headphones": cls.headphones,
            "speaker": cls.speaker,
            "keyboard": cls.keyboard,
            "grinder": cls.grinder,
            "mug": cls.mug,
            "lamp": cls.lamp,
            "notebook": cls.notebook,
            "backpack": cls.backpack,
            "tote": cls.tote,
            "bottle": cls.bottle,
            "thermos": cls.thermos,
            "beanie": cls.beanie,
        }


class Typography:
    def __init__(self, font_dir: Path) -> None:
        self._bold = self._load(font_dir, ("segoeuib.ttf", "arialbd.ttf"), 56)
        self._regular = self._load(font_dir, ("segoeui.ttf", "arial.ttf"), 28)
        self._small = self._load(font_dir, ("segoeuib.ttf", "arialbd.ttf"), 18)

    def draw(self, image: Image.Image, product: Placeholder) -> None:
        overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.text((56, 44), "SHOPDESK", font=self._small, fill=(255, 255, 255, 170))
        draw.text((56, 606), product.name, font=self._bold, fill=(255, 255, 255, 255))
        draw.text(
            (56, 682), product.category, font=self._regular, fill=(255, 255, 255, 205)
        )
        self._draw_label(draw, "PLATZHALTER  800 x 800")
        image.alpha_composite(overlay)

    def _draw_label(self, draw: ImageDraw.ImageDraw, label: str) -> None:
        left, top, right, bottom = self._small.getbbox(label)
        text_width, text_height = right - left, bottom - top
        pad_x, pad_y = 16, 9
        x1, y1 = SIZE - 56, SIZE - 56
        x0, y0 = x1 - text_width - 2 * pad_x, y1 - text_height - 2 * pad_y
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=(y1 - y0) // 2,
            fill=(255, 255, 255, 46),
            outline=(255, 255, 255, 110),
            width=2,
        )
        draw.text(
            (x0 + pad_x - left, y0 + pad_y - top),
            label,
            font=self._small,
            fill=(255, 255, 255, 235),
        )

    @staticmethod
    def _load(
        font_dir: Path, candidates: tuple[str, ...], size: int
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for name in candidates:
            path = font_dir / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
        return ImageFont.load_default(size)


class PlaceholderRenderer:
    def __init__(self, typography: Typography, shapes: dict[str, Shape]) -> None:
        self._typography = typography
        self._shapes = shapes

    def render(self, product: Placeholder) -> Image.Image:
        image = self._gradient(*product.gradient)
        image.alpha_composite(
            self._soft_ellipse((110, 30, 690, 560), (255, 255, 255, 62), 90)
        )
        image.alpha_composite(
            self._soft_ellipse((215, 545, 585, 605), (0, 0, 0, 120), 26)
        )
        image.alpha_composite(self._silhouette(product))
        self._typography.draw(image, product)
        return image.convert("RGB")

    def _silhouette(self, product: Placeholder) -> Image.Image:
        canvas = Image.new(
            "RGBA", (SIZE * SUPERSAMPLE, SIZE * SUPERSAMPLE), (0, 0, 0, 0)
        )
        pen = Pen(ImageDraw.Draw(canvas), SUPERSAMPLE)
        self._shapes[product.shape](pen, opaque(product.fill), opaque(product.detail))
        return canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS)

    @staticmethod
    def _gradient(start: str, end: str) -> Image.Image:
        mask = Image.frombytes(
            "L",
            (SIZE, SIZE),
            bytes(
                ((x + y) * 255) // (2 * (SIZE - 1))
                for y in range(SIZE)
                for x in range(SIZE)
            ),
        )
        first = Image.new("RGB", (SIZE, SIZE), hex_to_rgb(start))
        second = Image.new("RGB", (SIZE, SIZE), hex_to_rgb(end))
        return Image.composite(second, first, mask).convert("RGBA")

    @staticmethod
    def _soft_ellipse(box: Box, color: Rgba, blur: int) -> Image.Image:
        layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse(box, fill=color)
        return layer.filter(ImageFilter.GaussianBlur(blur))


class PlaceholderGenerator:
    def __init__(self, renderer: PlaceholderRenderer, out_dir: Path) -> None:
        self._renderer = renderer
        self._out_dir = out_dir

    def run(self, products: Sequence[Placeholder]) -> None:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        for product in products:
            target = self._out_dir / f"{product.slug}.png"
            self._renderer.render(product).save(target, "PNG", optimize=True)
            print(f"  {target.name:32s} {target.stat().st_size // 1024:4d} KB")
        print(f"{len(products)} Platzhalter nach {self._out_dir} geschrieben.")


def main() -> None:
    renderer = PlaceholderRenderer(Typography(FONT_DIR), Silhouettes.registry())
    PlaceholderGenerator(renderer, OUT_DIR).run(PRODUCTS)


if __name__ == "__main__":
    main()
