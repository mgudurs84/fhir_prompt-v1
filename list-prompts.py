import vertexai
from vertexai.preview import prompts

# Set your GCP project and region
PROJECT_ID = "your-gcp-project-id"
REGION = "us-central1"  # or your chosen region

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=REGION)

# List all prompts
prompt_list = prompts.list()

# Print all prompts' display names and IDs
for prompt_meta in prompt_list:
    print(f"Name: {prompt_meta.display_name} | Prompt ID: {prompt_meta.prompt_id}")
