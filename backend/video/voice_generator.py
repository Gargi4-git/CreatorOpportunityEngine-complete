import asyncio
from pathlib import Path

import edge_tts


OUTPUT_DIR = Path("data/generated/audio")


VOICE = "en-US-AriaNeural"


async def generate_voice(
    text: str,
    output_file: str = "narration.mp3"
):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = OUTPUT_DIR / output_file

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(str(output_path))

    return output_path


def create_voice(
    text: str,
    output_file: str = "narration.mp3"
):
    return asyncio.run(
        generate_voice(
            text,
            output_file
        )
    )


if __name__ == "__main__":

    sample_text = """
    Welcome to Creator Opportunity Engine.

    In this video, we will learn how to build
    a practical machine learning project.

    We will start with a real dataset,
    train a model, and deploy it.
    """

    output = create_voice(
        sample_text
    )

    print("\nVoice generated successfully!")
    print(f"Audio file: {output}")
