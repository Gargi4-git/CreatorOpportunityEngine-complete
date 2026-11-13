from backend.video.scene_generator import (
    create_scene_image
)

from backend.video.voice_generator import (
    create_voice
)

from backend.video.video_builder import (
    build_video
)


def main():

    print("\n================================")
    print("CREATOR VIDEO ENGINE TEST")
    print("================================")

    # Create scenes
    scene_1 = create_scene_image(
        title="Build Your First ML Project",
        body=(
            "Start with a real-world dataset "
            "and define a clear machine learning problem."
        ),
        scene_number=1
    )

    scene_2 = create_scene_image(
        title="Train Your Model",
        body=(
            "Clean the dataset, train a model, "
            "and evaluate its performance."
        ),
        scene_number=2
    )

    scene_3 = create_scene_image(
        title="Deploy Your Project",
        body=(
            "Turn your trained model into a usable "
            "application that people can interact with."
        ),
        scene_number=3
    )

    # Create narration
    narration = create_voice(
        """
        In this video, we will build a practical
        machine learning project.

        First, we choose a real-world dataset
        and define the problem.

        Then we train and evaluate our model.

        Finally, we deploy the project
        so it can be used as a real application.
        """,
        "test_narration.mp3"
    )

    # Build video
    video = build_video(
        scene_files=[
            scene_1,
            scene_2,
            scene_3
        ],
        audio_file=narration,
        output_file="test_creator_video.mp4",
        scene_duration=5
    )

    print("\n================================")
    print("TEST COMPLETE")
    print("================================")
    print(f"\nGenerated video:")
    print(video)


if __name__ == "__main__":
    main()
