import fitz  # PyMuPDF
from PIL import Image
import io

def extract_and_crop_images(pdf_path, crop_box):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    
    images = []
    
    # Iterate through each page
    for page_number in range(len(pdf_document)):
        page = pdf_document[page_number]
        # Extract images from the page
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]

            # Load the image with Pillow
            image = Image.open(io.BytesIO(image_bytes))
            
            # Crop the image using the provided crop box
            cropped_image = image.crop(crop_box)
            images.append(cropped_image)

            # Optionally save the cropped image
            cropped_image.save(f"img{page_number}.png")

    # Close the PDF document
    pdf_document.close()

    return images

# Define the crop box (x1, y1, x2, y2)
# crop_box = (655, 203, 1940, 2855)  # Example crop box
crop_box = (875, 130, 2120, 2855)  # Example crop box

# Call the function with your PDF path
extracted_images = extract_and_crop_images("Photos.pdf", crop_box)
