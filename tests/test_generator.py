from idea_generator import IdeaGenerator


def test_setup_parameters_preserves_existing_history(tmp_path):
    generator = IdeaGenerator(
        name="Test Generator",
        description="Test Description",
        model="test-model",
        embedding_model="test-embedding-model",
        generator_id="test",
    )
    generator.csv_filename = str(tmp_path / "ideas.csv")
    generator.setup_parameters({"title": "A concise idea title"})
    original_contents = (tmp_path / "ideas.csv").read_text()

    generator.setup_parameters({"title": "A concise idea title"})

    assert (tmp_path / "ideas.csv").read_text() == original_contents
    assert generator.Idea(title="QueuePilot").title == "QueuePilot"


def test_generator_can_disable_embeddings(tmp_path):
    generator = IdeaGenerator(
        name="Test Generator",
        description="Test Description",
        model="test-model",
        embedding_model="test-embedding-model",
        generator_id="test-no-embeddings",
        enable_embeddings=False,
    )
    generator.csv_filename = str(tmp_path / "ideas.csv")
    generator.setup_parameters({"title": "A concise idea title"})

    assert generator._find_similar_ideas({"title": "QueuePilot"}, [], 10) == []
