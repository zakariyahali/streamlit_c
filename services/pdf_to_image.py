import io
from pdf2image import convert_from_path
import os

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

# Example usage
# pdf_path = pdf_file  # Replace with your PDF file path
# output_folder = "C:/Users/tayma/Documents/09-form_reader_guines/guiness_form-app/media/images_from_pdf"
# poppler_path = r"C:\poppler-24.02.0\Library\bin"

# pdf_to_images(pdf_path, output_folder, poppler_path)
