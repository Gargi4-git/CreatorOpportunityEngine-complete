import re


def parse_script(script: str):
    """
    Convert Gemini's structured script
    into video scenes.
    """

    sections = []

    current_title = None
    current_content = []

    for raw_line in script.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # Remove markdown formatting
        clean_line = re.sub(
            r"[*#]",
            "",
            line
        ).strip()

        # Detect section headings
        heading_match = re.match(
            r"^(TITLE|HOOK|INTRODUCTION|SECTION\s+\d+|"
            r"PRACTICAL EXAMPLE|COMMON MISTAKES|"
            r"CONCLUSION|CALL TO ACTION)\s*:?\s*(.*)$",
            clean_line,
            re.IGNORECASE
        )

        if heading_match:

            if current_title and current_content:
                sections.append({
                    "title": current_title,
                    "content": " ".join(
                        current_content
                    )
                })

            current_title = heading_match.group(1).upper()

            remainder = heading_match.group(2).strip()

            current_content = []

            if remainder:
                current_content.append(remainder)

        else:

            if current_title:
                current_content.append(clean_line)

    if current_title and current_content:
        sections.append({
            "title": current_title,
            "content": " ".join(
                current_content
            )
        })

    return sections
