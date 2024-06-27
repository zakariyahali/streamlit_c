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

    convert_tocsv.convert_to_csv(os.path.join(json_dir, 'metadata.json'), os.path.join(csv_dir, 'metadata.csv'))
    st.success("JSON data combined and converted to CSV.")

    clean_and_save_csv_files(json_dir, csv_dir)
    st.success("CSV files cleaned and saved.")

def clean_and_save_csv_files(json_dir, csv_dir):
    for filename in os.listdir(json_dir):
        if filename.lower().endswith('.json'):
            file_path = os.path.join(json_dir, filename)
            df = pd.read_json(file_path)
            df_transposed = df.T.reset_index()
            df_transposed.columns = ['Question', 'Answer']
            cleaned_csv_filename = os.path.splitext(filename)[0] + '_cleaned.csv'
            df_transposed.to_csv(os.path.join(csv_dir, cleaned_csv_filename), index=False)
            st.success(f"Converted and cleaned {file_path} to {os.path.join(csv_dir, cleaned_csv_filename)}")

# Streamlit app
st.title("PDF to CSV Converter")
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