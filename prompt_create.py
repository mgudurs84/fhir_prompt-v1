import vertexai
from vertexai.preview.prompts import Prompt
from vertexai.preview import prompts

# 1. Set your GCP project and region
PROJECT_ID = "vertex-ai-demo-468112"
REGION = "us-central1"  # Change this if your resources are in another region

# 2. Initialize Vertex API
vertexai.init(project=PROJECT_ID, location=REGION)

# 3. Define system prompt and user prompt template
system_prompt = """
Act as a highly experienced IT Quality Testing specialist for FHIR resources and a specialist in ADT/CCDA to FHIR resource transformation. Your task is to generate comprehensive and complete test cases for FHIR resources based on the provided mapping specifications, ensuring full compliance with FHIR specifications and thorough validation of all mappings...
"""

user_prompt_template = """
current batch, batch number: {batch_number}
User Prompt: Please find the {layout} to {FHIR_Resource} template CSV file below:
mapping CSV template : {mapping_json_template}
Based on the system instructions and output formats provided, generate:
Functional
Regression
Edge test cases for the mapping CSV file that covers every possible attribute.
Expected Sample Output Format: {expected_sample_output_format}
"""

# 4. Prepare variables for this run (example only)
variables = [
    {
        "batch_number": "001",
        "layout": "ADT",
        "FHIR_Resource": "Patient",
        "mapping_json_template": '{"field1": "val1"}',
        "expected_sample_output_format": '{"some": "json"}'
    }
]

# 5. Create the Prompt object
prompt = Prompt(
    prompt_name="fhir_testcase_generator-sdk",
    prompt_data=user_prompt_template,
    variables=variables,
    model_name="gemini-2.5-flash-lite",  # Or another available model
    system_instruction=system_prompt
)

# 6. (Optional) Test prompt local generation before saving
for variable_set in prompt.variables:
    assembled = prompt.assemble_contents(**variable_set)
    print("\n--- Final Assembled Prompt ---\n")
    print(assembled)

# 7. Save prompt as a new version in Prompt Management
saved_prompt = prompts.create_version(prompt=prompt)

# 8. Print confirmation with usable IDs
print(
    "\nPrompt resource saved. Prompt ID:", saved_prompt.prompt_id,
    "Version:", saved_prompt.version_id
)

# 9. (Optional) Retrieve the prompt back using these IDs
# loaded_prompt = prompts.get(prompt_id=saved_prompt.prompt_id, version_id=saved_prompt.version_id)
# print("Loaded prompt:", loaded_prompt)
