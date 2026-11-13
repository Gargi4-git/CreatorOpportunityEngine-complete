from pathlib import Path
import subprocess

import imageio_ffmpeg


OUTPUT_DIR = Path("data/generated")


def get_ffmpeg():
    if hasattr(imageio_ffmpeg, "get_ffmpeg_exe"):
        return imageio_ffmpeg.get_ffmpeg_exe()
    if hasattr(imageio_ffmpeg, "get_ffmpeg"):
        return imageio_ffmpeg.get_ffmpeg()
    return "ffmpeg"


def get_audio_duration(audio_file):
    ffmpeg = get_ffmpeg()
    res = subprocess.run(
        [ffmpeg, "-i", str(audio_file), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    import re
    match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 5.0


def concat_audio_files(audio_files, output_file="combined_narration.mp3"):
    ffmpeg = get_ffmpeg()
    output_path = OUTPUT_DIR / "audio" / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    list_path = OUTPUT_DIR / "audio" / "audio_list.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for audio in audio_files:
            p = Path(audio).resolve()
            f.write(f"file '{p.as_posix()}'\n")

    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path



def estimate_scene_duration(text: str) -> float:
    """
    Estimate narration duration from text.
    Average speaking speed: approximately 145 words per minute.
    """
    words = len(text.split())
    words_per_second = 145 / 60
    duration = words / words_per_second
    duration += 0.8  # breathing room
    duration = max(3.5, duration)
    duration = min(18.0, duration)
    return round(duration, 2)


def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def create_subtitle_file(
    scenes,
    durations,
    output_file="creator_subtitles.srt"
):
    subtitle_path = OUTPUT_DIR / output_file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    current_time = 0.0

    with open(subtitle_path, "w", encoding="utf-8") as file:
        for index, scene in enumerate(scenes, start=1):
            duration = durations[index - 1]
            start = current_time
            end = current_time + duration

            file.write(f"{index}\n")
            file.write(
                f"{format_timestamp(start)} --> {format_timestamp(end)}\n"
            )
            file.write(f"{scene['content']}\n\n")

            current_time = end

    return subtitle_path


def build_video(
    scene_files,
    audio_file,
    scenes=None,
    output_file="creator_video.mp4"
):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = get_ffmpeg()
    output_path = OUTPUT_DIR / output_file

    if scenes:
        durations = [
            estimate_scene_duration(scene["content"])
            for scene in scenes
        ]
    else:
        durations = [6.0 for _ in scene_files]

    print("\nScene durations:")
    for index, duration in enumerate(durations, start=1):
        print(f"Scene {index}: {duration}s")

    concat_file = OUTPUT_DIR / "scenes.txt"

    with open(concat_file, "w", encoding="utf-8") as file:
        for scene, duration in zip(scene_files, durations):
            scene_path = Path(scene).resolve()
            file.write(f"file '{scene_path.as_posix()}'\n")
            file.write(f"duration {duration}\n")

        if scene_files:
            final_scene = Path(scene_files[-1]).resolve()
            file.write(f"file '{final_scene.as_posix()}'\n")

    subtitle_path = None
    if scenes:
        subtitle_path = create_subtitle_file(scenes, durations)

    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-i",
        str(audio_file),
    ]

    # Add subtitles if libass filter is supported
    if subtitle_path:
        sub_posix = Path(subtitle_path).as_posix()
        # For Windows FFmpeg subtitles filter: escape colon e.g. C\\:/...
        sub_escaped = sub_posix.replace(":", "\\:")
        command.extend([
            "-vf",
            f"subtitles={sub_escaped}:force_style='FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00111827,BorderStyle=3,MarginV=35'",
        ])

    command.extend([
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ])

    print("\nBuilding video with FFmpeg...")
    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # Fallback if subtitles filter fails (e.g. fontconfig/libass environment)
        fallback_cmd = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-i",
            str(audio_file),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        subprocess.run(fallback_cmd, check=True, capture_output=True)

    print(f"\nVideo created successfully at: {output_path}")
    if subtitle_path:
        print(f"Subtitle file: {subtitle_path}")

    return output_path
