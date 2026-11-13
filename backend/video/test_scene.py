from backend.video.scene_generator import create_scene_image


if __name__ == "__main__":

    scene = create_scene_image(
        title="Build Your First ML Project",
        body=(
            "Learn how to turn a real-world dataset "
            "into a practical machine learning project "
            "that you can deploy and showcase."
        ),
        scene_number=1
    )

    print("\nScene created successfully!")
    print(scene)
