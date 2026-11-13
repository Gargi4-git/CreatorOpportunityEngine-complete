from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTPUT_DIR = Path("data/generated/scenes")


FORMATS = {
    "youtube": {
        "width": 1280,
        "height": 720,
    },
    "shorts": {
        "width": 720,
        "height": 1280,
    },
}


def get_font(size):
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]

    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def wrap_text(
    draw,
    text,
    font,
    max_width
):
    words = text.split()

    lines = []
    current = ""

    for word in words:

        test = (
            current + " " + word
        ).strip()

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=font
        )

        if bbox[2] <= max_width:
            current = test

        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


def create_scene_image(
    title: str,
    body: str,
    scene_number: int,
    video_format: str = "youtube",
    total_scenes: int = 1,
):
    if video_format not in FORMATS:
        raise ValueError(
            "video_format must be 'youtube' or 'shorts'"
        )

    width = FORMATS[
        video_format
    ]["width"]

    height = FORMATS[
        video_format
    ]["height"]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    image = Image.new(
        "RGB",
        (width, height),
        "#f8fafc"
    )

    draw = ImageDraw.Draw(image)

    # ----------------------------------
    # Fonts
    # ----------------------------------

    if video_format == "youtube":

        label_font = get_font(20)
        title_font = get_font(56)
        body_font = get_font(30)
        small_font = get_font(18)

        margin = 80

    else:

        label_font = get_font(18)
        title_font = get_font(48)
        body_font = get_font(28)
        small_font = get_font(17)

        margin = 55

    # ----------------------------------
    # Header
    # ----------------------------------

    draw.text(
        (margin, 45),
        "CREATOR OPPORTUNITY ENGINE",
        font=label_font,
        fill="#64748b"
    )

    # ----------------------------------
    # Progress indicator
    # ----------------------------------

    progress_width = (
        230 if video_format == "youtube"
        else 160
    )

    progress_x = width - margin - progress_width
    progress_y = 55

    draw.rounded_rectangle(
        (
            progress_x,
            progress_y,
            progress_x + progress_width,
            progress_y + 7
        ),
        radius=4,
        fill="#dbe3ed"
    )

    if total_scenes > 0:

        completed_width = (
            progress_width
            * scene_number
            / total_scenes
        )

        draw.rounded_rectangle(
            (
                progress_x,
                progress_y,
                progress_x + completed_width,
                progress_y + 7
            ),
            radius=4,
            fill="#111827"
        )

    # ----------------------------------
    # Scene indicator
    # ----------------------------------

    draw.text(
        (
            progress_x,
            progress_y + 17
        ),
        f"{scene_number} / {total_scenes}",
        font=small_font,
        fill="#64748b"
    )

    # ----------------------------------
    # Accent block
    # ----------------------------------

    accent_x = margin
    accent_y = (
        145 if video_format == "youtube"
        else 170
    )

    draw.rounded_rectangle(
        (
            accent_x,
            accent_y,
            accent_x + 8,
            accent_y + 95
        ),
        radius=4,
        fill="#111827"
    )

    # ----------------------------------
    # Title
    # ----------------------------------

    title_x = margin + 28
    title_y = accent_y - 5

    title_lines = wrap_text(
        draw,
        title,
        title_font,
        width - margin * 2 - 30
    )

    current_y = title_y

    for line in title_lines:

        draw.text(
            (
                title_x,
                current_y
            ),
            line,
            font=title_font,
            fill="#101b30"
        )

        current_y += 68

    # ----------------------------------
    # Body
    # ----------------------------------

    body_y = (
        300 if video_format == "youtube"
        else 390
    )

    body_lines = wrap_text(
        draw,
        body,
        body_font,
        width - margin * 2
    )

    for line in body_lines:

        draw.text(
            (
                margin,
                body_y
            ),
            line,
            font=body_font,
            fill="#33445d"
        )

        body_y += 48

    # ----------------------------------
    # Bottom information
    # ----------------------------------

    footer_y = height - (
        65 if video_format == "youtube"
        else 95
    )

    draw.line(
        (
            margin,
            footer_y,
            width - margin,
            footer_y
        ),
        fill="#d8e0ea",
        width=2
    )

    draw.text(
        (
            margin,
            footer_y + 18
        ),
        "Built from real audience intelligence",
        font=small_font,
        fill="#718096"
    )

    # ----------------------------------
    # Save
    # ----------------------------------

    format_folder = (
        OUTPUT_DIR / video_format
    )

    format_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        format_folder
        / f"scene_{scene_number:02d}.png"
    )

    image.save(
        output_path
    )

    return output_path
