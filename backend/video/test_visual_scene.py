from backend.video.scene_generator import (
    create_scene_image
)


def main():
    scene_yt = create_scene_image(
        title="Build Real Machine Learning Projects",
        body=(
            "Stop following only theoretical tutorials. "
            "Start with a real dataset, solve a practical "
            "problem, and build something you can actually deploy."
        ),
        scene_number=2,
        video_format="youtube",
        total_scenes=7
    )
    print("\nYouTube Scene created:")
    print(scene_yt)

    scene_shorts = create_scene_image(
        title="Build Real Machine Learning Projects",
        body=(
            "Stop following only theoretical tutorials. "
            "Start with a real dataset, solve a practical "
            "problem, and build something you can actually deploy."
        ),
        scene_number=2,
        video_format="shorts",
        total_scenes=7
    )
    print("\nShorts Scene created:")
    print(scene_shorts)


if __name__ == "__main__":
    main()
