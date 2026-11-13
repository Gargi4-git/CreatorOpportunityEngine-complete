import re
from pathlib import Path

from backend.ai.creator_studio import load_best_opportunity, build_context
from backend.ai.gemini import generate_opportunity
from backend.video.scene_generator import create_scene_image
from backend.video.voice_generator import create_voice
from backend.video.video_builder import (
    build_video,
    get_audio_duration,
    concat_audio_files,
)


def generate_video_scenes_script(opportunity=None):
    if not opportunity:
        opportunity = load_best_opportunity()

    context = build_context(opportunity)

    prompt = f"""
You are an expert educational video director for YouTube creators.

Create a concise, high-impact 5-scene video script based on this audience demand:
{context}

Format your response EXACTLY like this:

SCENE 1: HOOK
A punchy 1-2 sentence hook calling out the viewer's problem.

SCENE 2: AUDIENCE PROBLEM
Explain why learners struggle with this and why it matters.

SCENE 3: SOLUTION BLUEPRINT
Provide the clear practical blueprint or framework to solve it.

SCENE 4: PRACTICAL EXAMPLE
A concrete real-world project or implementation example.

SCENE 5: CALL TO ACTION
A strong conclusion and call to action for the creator's channel.

Keep each scene to 2-3 clear sentences so it is engaging for video narration.
Do not invent fake audience statistics.
"""

    raw_script = generate_opportunity(prompt)
    return raw_script, opportunity


def parse_video_scenes(raw_script: str):
    """
    Parse the 5 scenes from the Gemini script.
    """
    scenes = []
    current_title = None
    current_lines = []

    for raw_line in raw_script.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        clean = re.sub(r"[*#]", "", line).strip()

        match = re.match(
            r"^(SCENE\s*\d+\s*[:\-]?\s*([A-Za-z\s]+)|HOOK|PROBLEM|AUDIENCE PROBLEM|SOLUTION|SOLUTION BLUEPRINT|PRACTICAL EXAMPLE|EXAMPLE|CALL TO ACTION|CONCLUSION)\s*:?\s*(.*)$",
            clean,
            re.IGNORECASE,
        )

        if match:
            if current_title and current_lines:
                scenes.append({
                    "title": current_title,
                    "content": " ".join(current_lines),
                })
            # Title
            title = match.group(2) if match.group(2) else match.group(1)
            current_title = title.strip().upper()
            current_lines = []
            if match.group(3):
                current_lines.append(match.group(3).strip())
        else:
            if current_title:
                current_lines.append(clean)
            else:
                current_title = "INTRODUCTION"
                current_lines.append(clean)

    if current_title and current_lines:
        scenes.append({
            "title": current_title,
            "content": " ".join(current_lines),
        })

    # Fallback if parsing failed to extract at least 3 scenes
    if len(scenes) < 3:
        paragraphs = [p.strip() for p in raw_script.split("\n\n") if p.strip()]
        scenes = []
        titles = ["HOOK", "PROBLEM", "SOLUTION", "DEMO", "CALL TO ACTION"]
        for i, para in enumerate(paragraphs[:5]):
            scenes.append({
                "title": titles[i] if i < len(titles) else f"SCENE {i+1}",
                "content": para,
            })

    return scenes


def generate_complete_opportunity_video(opportunity=None, output_filename="creator_video.mp4"):
    """
    Full End-to-End Video Generation Pipeline:
    Opportunity -> Script -> Visual Scenes -> AI Narration -> Synchronized MP4
    """
    raw_script, opp = generate_video_scenes_script(opportunity)
    scenes = parse_video_scenes(raw_script)

    scene_images = []
    scene_audios = []
    scene_durations = []

    for idx, scene in enumerate(scenes):
        scene_num = idx + 1
        title = scene["title"]
        body = scene["content"]

        # 1. Visual Frame
        img_path = create_scene_image(
            title=title,
            body=body,
            scene_number=scene_num,
        )
        scene_images.append(img_path)

        # 2. Scene Voice Audio
        audio_name = f"scene_{scene_num:02d}_audio.mp3"
        audio_path = create_voice(body, output_file=audio_name)
        scene_audios.append(audio_path)

        # 3. Synchronized Duration
        dur = get_audio_duration(audio_path) + 0.4
        scene_durations.append(dur)

    # 4. Master Narration Track
    master_audio = concat_audio_files(scene_audios, output_file="master_narration.mp3")

    # 5. Build MP4 Video
    video_path = build_video(
        scene_files=scene_images,
        audio_file=master_audio,
        output_file=output_filename,
        scene_duration=scene_durations,
    )

    total_duration = round(sum(scene_durations), 1)

    return {
        "status": "success",
        "video_filename": output_filename,
        "video_url": f"http://127.0.0.1:8000/media/{output_filename}",
        "duration": total_duration,
        "scenes_count": len(scenes),
        "scenes": scenes,
        "opportunity": {
            "cluster_id": opp["cluster_id"],
            "opportunity_score": opp["opportunity_score"],
            "comment_count": opp["comment_count"],
            "total_engagement": opp["total_engagement"],
            "audience_problem": opp.get("audience_problem", ""),
        },
    }
