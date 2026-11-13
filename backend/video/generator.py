from pathlib import Path

from backend.ai.creator_studio import (
    load_best_opportunity,
    generate_video_script,
)
from backend.video.script_parser import parse_script
from backend.video.scene_generator import create_scene_image
from backend.video.voice_generator import create_voice
from backend.video.video_builder import build_video


OUTPUT_DIR = Path("data/generated")


def create_video_from_opportunity(video_format: str = "youtube"):
    print("\n====================================")
    print("CREATOR OPPORTUNITY VIDEO GENERATOR")
    print(f"Format: {video_format.upper()}")
    print("====================================")

    # 1. Get best audience opportunity
    print("\n[1/6] Loading best opportunity...")
    opportunity = load_best_opportunity()
    print(f"Opportunity score: {opportunity['opportunity_score']}")
    print(f"Audience problem: {opportunity['audience_problem']}")

    # 2. Generate Gemini script
    print("\n[2/6] Generating video script...")
    script = generate_video_script()
    print("Script generated.")

    # 3. Convert script to scenes
    print("\n[3/6] Creating video scenes...")
    scenes = parse_script(script)

    if not scenes:
        raise ValueError("Gemini script could not be converted into scenes.")

    if len(scenes) > 6:
        scenes = scenes[:6]

    print(f"Scenes detected: {len(scenes)}")

    # 4. Generate scene images
    print("\n[4/6] Generating scene visuals...")
    scene_files = []
    for index, scene in enumerate(scenes, start=1):
        print(f"Creating scene {index}: {scene['title']}")
        scene_file = create_scene_image(
            title=scene["title"],
            body=scene["content"],
            scene_number=index,
            video_format=video_format,
            total_scenes=len(scenes),
        )
        scene_files.append(scene_file)

    # 5. Generate narration
    print("\n[5/6] Generating AI narration...")
    narration_text = " ".join(scene["content"] for scene in scenes)
    narration = create_voice(narration_text, "creator_narration.mp3")
    print(f"Narration created: {narration}")

    # 6. Build final video
    print("\n[6/6] Building final MP4...")
    video = build_video(
        scene_files=scene_files,
        audio_file=narration,
        scenes=scenes,
        output_file="creator_video.mp4",
    )

    print("\n====================================")
    print("VIDEO GENERATION COMPLETE")
    print("====================================")
    print(f"\nVideo: {video}")

    return {
        "video_path": str(video),
        "video_format": video_format,
        "opportunity_score": opportunity["opportunity_score"],
        "audience_problem": opportunity["audience_problem"],
        "scene_count": len(scenes),
        "scenes": scenes,
    }


if __name__ == "__main__":
    create_video_from_opportunity()
