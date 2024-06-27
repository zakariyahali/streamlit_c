from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import base64

# api key config
load_dotenv()
OpenAI.api_key = os.getenv('OPENAI_API_KEY')

client = OpenAI()
##############################################################

def load_json_schema(schema_file: str) -> dict:
    with open(schema_file, 'r') as file:
        return json.load(file)

def process_image(image_path: str, form_schema: dict, output_dir: str):
    try:
        # Open the local image file in binary mode
        with open(image_path, 'rb') as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

        response = client.chat.completions.create(
            model='gpt-4o',
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "provide JSON file that represents this document. Use this JSON Schema: " +
                            json.dumps(form_schema)},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
        )

        if response and response.choices and response.choices[0].message.content:
            content = response.choices[0].message.content
            try:
                json_data = json.loads(content)
                filename_without_extension = os.path.splitext(os.path.basename(image_path))[0]
                json_filename = os.path.join(output_dir, f"{filename_without_extension}.json")

                with open(json_filename, 'w') as file:
                    json.dump(json_data, file, indent=4)

                print(f"JSON data saved to {json_filename}")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON for {image_path}: {e}")
                print(f"Response content: {content}")
        else:
            print(f"No valid response for {image_path}")
    except Exception as e:
        print(f"Error processing {image_path}: {e}")

def process_images_in_directory(image_dir: str, schema_file: str, output_dir: str):
    form_schema = load_json_schema(schema_file)
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    for filename in os.listdir(image_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            image_path = os.path.join(image_dir, filename)
            process_image(image_path, form_schema, output_dir)
    
    # Combine all JSON files into a single metadata JSON file
    combine_json_files(output_dir, os.path.join(output_dir, 'metadata.json'))

def combine_json_files(input_dir: str, output_file: str):
    combined_data = {}

    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.json'):
            file_path = os.path.join(input_dir, filename)
            with open(file_path, 'r') as file:
                try:
                    file_data = json.load(file)
                    file_id = os.path.splitext(filename)[0]
                    combined_data[file_id] = file_data
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON file {file_path}: {e}")
                    continue

    with open(output_file, 'w') as file:
        json.dump(combined_data, file, indent=4)

    print(f"Combined JSON data saved to {output_file}")

