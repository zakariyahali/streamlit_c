import streamlit as st
import os
import pandas as pd
import json
import base64
from pdf2image import convert_from_path
import openai
from openai import OpenAI, OpenAIError
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
    schema_file = 'form_schema.json'
    process_images.process_images_in_directory(image_dir, schema_file, json_dir)
    st.success("Images processed to JSON.")

    clean_and_save_individual_csv_files(json_dir, csv_dir)
    clean_and_save_merged_csv_files(json_dir, csv_dir)
    st.success("CSV files cleaned and saved.")

def clean_and_save_individual_csv_files(json_dir, csv_dir):
    schema_file = 'form_schema.json'
    with open(schema_file, 'r') as file:
        schema = json.load(file)

    questions = [(prop, details.get("description", prop)) for prop, details in schema['properties'].items()]

    for filename in os.listdir(json_dir):
        if filename.lower().endswith('.json'):
            file_path = os.path.join(json_dir, filename)
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                
                if not isinstance(data, dict):
                    st.error(f"Unexpected format in file {file_path}, skipping.")
                    continue

                answers = []
                for question_key, question_desc in questions:
                    answer = extract_answer(data, question_key)
                    answers.append((question_desc, answer))

                df = pd.DataFrame(answers, columns=["Question", "Answer"])
                csv_filename = os.path.join(csv_dir, f"{os.path.splitext(filename)[0]}_cleaned.csv")
                df.to_csv(csv_filename, index=False)
                st.write(f"Generated CSV file: {csv_filename}")

            except json.JSONDecodeError as e:
                st.error(f"Error decoding JSON for {file_path}: {e}")
            except ValueError as e:
                st.error(f"Error processing file {file_path}: {e}")

def clean_and_save_merged_csv_files(json_dir, csv_dir):
    schema_file = 'form_schema.json'
    with open(schema_file, 'r') as file:
        schema = json.load(file)

    questions = [(prop, details.get("description", prop)) for prop, details in schema['properties'].items()]

    json_files = sorted(os.listdir(json_dir))
    form_data = []

    for idx in range(0, len(json_files), 2):
        form_answers = []

        if idx < len(json_files):
            file_path = os.path.join(json_dir, json_files[idx])
            form_answers += extract_answers_from_page(file_path, questions[:len(questions)//2])

        if idx + 1 < len(json_files):
            file_path = os.path.join(json_dir, json_files[idx + 1])
            form_answers += extract_answers_from_page(file_path, questions[len(questions)//2:])

        if len(form_answers) != len(questions):
            st.error(f"Length of answers ({len(form_answers)}) does not match length of questions ({len(questions)}) for form {idx // 2 + 1}, skipping.")
            continue

        form_data.append(form_answers)

    form_df = pd.DataFrame(form_data, columns=[q[1] for q in questions]).T
    form_df.columns = [f"Form_{i+1}" for i in range(len(form_data))]

    for idx in range(0, len(json_files), 2):
        form_num = idx // 2 + 1
        merged_csv_filename = f'form_{form_num}_merged.csv'
        form_df[[f"Form_{form_num}"]].to_csv(os.path.join(csv_dir, merged_csv_filename), index_label="Question")
        st.write(f"Generated Merged CSV file: {merged_csv_filename}")

def extract_answers_from_page(file_path, questions):
    answers = []
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)

        if not isinstance(data, dict):
            st.error(f"Unexpected format in file {file_path}, skipping.")
            return answers

        for question_key, _ in questions:
            answer = extract_answer(data, question_key)
            answers.append(answer)

    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON for {file_path}: {e}")
    except ValueError as e:
        st.error(f"Error processing file {file_path}: {e}")

    return answers

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

        # Summary of the process
        num_images = len(os.listdir(image_dir))
        num_csv_files = len([name for name in os.listdir(csv_dir) if name.lower().endswith('.csv')])
        st.write(f"Process Summary: {num_images} images processed, {num_csv_files} CSV files generated.")

        # Display individual cleaned CSV files
        st.write("### Individual Cleaned CSV Files")
        for filename in sorted(os.listdir(csv_dir)):
            if filename.lower().endswith('_cleaned.csv') and 'metadata' not in filename:
                page_number = filename.split('_')[0].replace('page', 'Page ')
                st.write(f"**{page_number}**")
                st.dataframe(pd.read_csv(os.path.join(csv_dir, filename)))

        # Display merged CSV files
        st.write("### Merged CSV Files")
        for idx in range(1, (num_images // 2) + 1):
            merged_csv_filename = f'form_{idx}_merged.csv'
            if os.path.exists(os.path.join(csv_dir, merged_csv_filename)):
                st.write(f"#### Form {idx}")
                st.dataframe(pd.read_csv(os.path.join(csv_dir, merged_csv_filename)))
                st.write(f"Merged CSV for Form {idx} is created by combining Page {2 * idx - 1} and Page {2 * idx}.")

        # Explain other files created
        st.write("### Other Files Created")
        st.write(f"All JSON files and their corresponding CSV files are saved in the `generated_files` directory inside `{base_dir}`.")
        st.write("You can download these files from their directories for further use.")