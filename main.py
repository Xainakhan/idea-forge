"""Generate one structured idea locally, without the HTTP layer."""

import json

from idea_generator.app import generator


if __name__ == "__main__":
    idea = generator.generate_idea("Focus on an operations automation product.")
    print(json.dumps(idea, indent=2))
