import streamlit as st
import os
import pandas as pd
import json
import base64
import tempfile
from pdf2image import convert_from_path
from dotenv import load_dotenv
from openai import OpenAI
import io
from pdf2image import convert_from_path
import os

# Load environment variables from .env file
load_dotenv()
OpenAI.api_key = st.secrets["openai_api_key"]
client = OpenAI()



def pdf_to_images(pdf_path, output_folder, poppler_path):
    # Ensure the output directory exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Convert PDF pages to images
    pages = convert_from_path(pdf_path, poppler_path=poppler_path)
    
    for page_number, page in enumerate(pages):
        image_name = f"page{page_number + 1}.jpg"
        image_path = os.path.join(output_folder, image_name)
        
        # Save the image
        page.save(image_path, "JPEG")
    
    print("Pages converted and saved as images.")

def convert_json_to_csv(json_file, csv_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
    df = pd.json_normalize(data, sep='_')
    df.to_csv(csv_file, index=False)

def clean_csv(file_path, output_path):
    df = pd.read_csv(file_path)
    df_transposed = df.T.reset_index()
    df_transposed.columns = ['Question', 'Answer']
    df_transposed.to_csv(output_path, index=False)

def process_image(image_path, form_schema, output_dir):
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
        max_tokens=500,
    )

    if response and response.choices and response.choices[0].message.content:
        content = response.choices[0].message.content
        try:
            json_data = json.loads(content)
            filename_without_extension = os.path.splitext(os.path.basename(image_path))[0]
            json_filename = os.path.join(output_dir, f"{filename_without_extension}.json")

            with open(json_filename, 'w') as file:
                json.dump(json_data, file, indent=4)

            return json_filename
        except json.JSONDecodeError as e:
            st.error(f"Error decoding JSON for {image_path}: {e}")
            st.error(f"Response content: {content}")
            return None
    else:
        st.error(f"No valid response for {image_path}")
        return None

def process_images_in_directory(image_dir, schema_file, json_output_dir):
    with open(schema_file, 'r') as file:
        form_schema = json.load(file)
    
    os.makedirs(json_output_dir, exist_ok=True)
    
    for filename in os.listdir(image_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            image_path = os.path.join(image_dir, filename)
            json_filename = process_image(image_path, form_schema, json_output_dir)
            if json_filename:
                st.write(f"Processed {filename} to {json_filename}")
    
    combine_json_files(json_output_dir, os.path.join(json_output_dir, 'metadata.json'))

def combine_json_files(input_dir, output_file):
    combined_data = {}

    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.json'):
            file_path = os.path.join(input_dir, filename)
            with open(file_path, 'r') as file:
                file_data = json.load(file)
                file_id = os.path.splitext(filename)[0]
                combined_data[file_id] = file_data

    with open(output_file, 'w') as file:
        json.dump(combined_data, file, indent=4)

    st.write(f"Combined JSON data saved to {output_file}")



#------> Streamlit UI
st.title("PDF and Image GEN-AI Processor")

# Step 1: File upload
uploaded_pdf = st.file_uploader("Choose a PDF file", type="pdf")
#poppler_path = st.text_input("Enter the Poppler path", "C:\\poppler-24.02.0\\Library\\bin")

if uploaded_pdf is not None:
    # Use Streamlit's temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = os.path.join(temp_dir, uploaded_pdf.name)

        # Save uploaded PDF to the temporary directory
        with open(pdf_path, "wb") as f:
            f.write(uploaded_pdf.getbuffer())

        # Create a dedicated directory for all generated files
        generated_files_dir = os.path.join(temp_dir, "generated_files")
        os.makedirs(generated_files_dir, exist_ok=True)

        # Set paths for images, JSON, and CSV outputs
        image_dir = os.path.join(generated_files_dir, "images")
        json_output_dir = os.path.join(generated_files_dir, "json")
        csv_output_dir = os.path.join(generated_files_dir, "csv")

        os.makedirs(image_dir, exist_ok=True)
        os.makedirs(json_output_dir, exist_ok=True)
        os.makedirs(csv_output_dir, exist_ok=True)

        # Display the paths to the user
        st.write("Images will be saved to:", image_dir)
        st.write("JSON files will be saved to:", json_output_dir)
        st.write("CSV files will be saved to:", csv_output_dir)

        # Step 2: Button to start processing
        if st.button("Start Processing"):
            # Process PDF to images
            with st.spinner("Converting PDF to images..."):
                pdf_to_image.pdf_to_images(pdf_path, image_dir, poppler_path)
                st.write("PDF converted to images")

            # Process images to JSON
            with st.spinner("Converting images to JSON..."):
                process_images_in_directory(image_dir, "form_schema.json", json_output_dir)
                st.write("Images converted to JSON")

            # Combine JSON and convert to CSV
            with st.spinner("Combining JSON files and converting to CSV..."):
                combined_json_path = os.path.join(json_output_dir, 'metadata.json')
                convert_json_to_csv(combined_json_path, os.path.join(csv_output_dir, 'metadata.csv'))
                clean_csv(os.path.join(csv_output_dir, 'metadata.csv'), os.path.join(csv_output_dir, 'metadata_cleaned.csv'))
                st.write("Combined JSON converted to CSV and cleaned")

            # Convert individual JSON files to CSV and clean them
            with st.spinner("Converting individual JSON files to CSV..."):
                for filename in os.listdir(json_output_dir):
                    if filename.endswith('.json') and filename != 'metadata.json':
                        json_path = os.path.join(json_output_dir, filename)
                        csv_path = os.path.join(csv_output_dir, f"{os.path.splitext(filename)[0]}.csv")
                        cleaned_csv_path = os.path.join(csv_output_dir, f"{os.path.splitext(filename)[0]}_cleaned.csv")

                        convert_json_to_csv(json_path, csv_path)
                        clean_csv(csv_path, cleaned_csv_path)
                        st.write(f"Converted and cleaned {json_path} to {cleaned_csv_path}")

            st.success("Processing completed!")

            # Display the CSV files
            for filename in os.listdir(csv_output_dir):
                if filename.endswith('_cleaned.csv'):
                    st.write(f"Displaying {filename}")
                    file_path = os.path.join(csv_output_dir, filename)
                    df = pd.read_csv(file_path)
                    st.dataframe(df)
else:
    st.warning("Please upload a PDF file to proceed.")
