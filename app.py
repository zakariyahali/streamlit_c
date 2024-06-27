import streamlit as st
import os
import pandas as pd
import json
import base64
import tempfile
from pdf2image import convert_from_path
import openai
from openai import OpenAI, OpenAIError
import io
import fitz
from services import pdf_to_image, process_images, convert_tocsv

openai.api_key = st.secrets["OPENAI_API_KEY"]
api_key = openai.api_key
OpenAI.api_key = api_key
if not api_key:
    st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI()

def convert_pdf_to_images(pdf_path, image_dir):
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    
    pdf_document = fitz.open(pdf_path)
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        image_path = os.path.join(image_dir, f"page{page_num + 1}.png")
        pix.save(image_path)
    
    st.success("PDF converted to images.")

def process_files(image_dir, json_dir, csv_dir):
    schema_file = 'form_schema.json'  # Ensure form_schema.json is available in the directory
    process_images.process_images_in_directory(image_dir, schema_file, json_dir)
    st.success("Images processed to JSON.")

    combine_json_files(json_dir)
    st.success("JSON data combined.")

    clean_and_save_csv_files(json_dir, csv_dir)
    st.success("CSV files cleaned and saved.")

def combine_json_files(json_dir):
    combined_data = {}

    for filename in os.listdir(json_dir):
        if filename.lower().endswith('.json'):
            file_path = os.path.join(json_dir, filename)
            with open(file_path, 'r') as file:
                file_data = json.load(file)
                file_id = os.path.splitext(filename)[0]
                combined_data[file_id] = file_data

    combined_json_path = os.path.join(json_dir, 'metadata.json')
    with open(combined_json_path, 'w') as file:
        json.dump(combined_data, file, indent=4)

    st.write(f"Combined JSON data saved to {combined_json_path}")

def clean_and_save_csv_files(json_dir, csv_dir):
    schema_file = 'form_schema.json'
    with open(schema_file, 'r') as file:
        schema = json.load(file)

    # Extract all questions from the schema
    questions = [prop for prop in schema['properties']]

    # Initialize DataFrame with questions
    df = pd.DataFrame({"Question": questions})

    json_files = sorted(os.listdir(json_dir))
    form_data = {}
    
    # Read each JSON file and combine pages to form complete forms
    for idx in range(0, len(json_files), 2):
        form_number = idx // 2 + 1
        form_answers = []

        for page_offset in range(2):
            if idx + page_offset < len(json_files):
                filename = json_files[idx + page_offset]
                file_path = os.path.join(json_dir, filename)
                try:
                    with open(file_path, 'r') as file:
                        data = json.load(file)

                    if not isinstance(data, dict):
                        st.error(f"Unexpected format in file {file_path}, skipping.")
                        continue

                    # Extract answers for each question
                    for question in questions:
                        answer = extract_answer(data, question)
                        form_answers.append(answer)

                except json.JSONDecodeError as e:
                    st.error(f"Error decoding JSON for {file_path}: {e}")
                except ValueError as e:
                    st.error(f"Error processing file {file_path}: {e}")

        # Ensure the form_answers list has the same length as questions
        if len(form_answers) != len(questions):
            st.error(f"Length of answers ({len(form_answers)}) does not match length of questions ({len(questions)}) for form {form_number}, skipping.")
            continue

        form_data[f"Form_{form_number}"] = form_answers

    # Create a DataFrame from form_data
    form_df = pd.DataFrame(form_data, index=questions).reset_index()
    form_df.columns = ["Question"] + list(form_df.columns[1:])
    
    # Save the cleaned DataFrame to a new CSV file
    cleaned_csv_filename = 'metadata_cleaned.csv'
    form_df.to_csv(os.path.join(csv_dir, cleaned_csv_filename), index=False)
    st.success(f"Cleaned CSV data saved to {os.path.join(csv_dir, cleaned_csv_filename)}")

def extract_answer(data, question):
    keys = question.split('.')
    answer = data
    try:
        for key in keys:
            if isinstance(answer, dict):
                answer = answer.get(key, "")
            else:
                return ""
    except Exception as e:
        return ""
    return answer

# Streamlit app
st.title("Gen-AI: PDF & Image to CSV Converter")
st.write("Upload a PDF file and choose the directories for the output files.")

pdf_file = st.file_uploader("Choose a PDF file", type="pdf")

if pdf_file is not None:
    pdf_path = pdf_file.name
    with open(pdf_path, "wb") as f:
        f.write(pdf_file.getbuffer())

    base_dir = os.path.dirname(pdf_path)
    image_dir = os.path.join(base_dir, "generated_files/images_from_pdf")
    json_dir = os.path.join(base_dir, "generated_files/json_output")
    csv_dir = os.path.join(base_dir, "generated_files/csv_output")

    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)

    st.write(f"Image directory: {image_dir}")
    st.write(f"JSON directory: {json_dir}")
    st.write(f"CSV directory: {csv_dir}")

    if st.button("Start Processing"):
        with st.spinner("Converting PDF to images..."):
            convert_pdf_to_images(pdf_path, image_dir)

        with st.spinner("Processing images..."):
            process_files(image_dir, json_dir, csv_dir)

        st.success("All processing complete!")
        
        for filename in os.listdir(csv_dir):
            if filename.lower().endswith('.csv'):
                st.write(f"Generated CSV file: {filename}")
                st.dataframe(pd.read_csv(os.path.join(csv_dir, filename)))
