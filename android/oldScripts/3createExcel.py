import os
import pandas as pd
from PIL import Image
import pytesseract
from tqdm import tqdm


# Main script
image_dir = 'amiiImages/'
final_words = []
output_file='AMII_Data.xlsx'


def extract_data_to_excel(final_words, output_file):
    extracted_data = []
    
    for entry in final_words:
        if len(entry) < 13:  # Ensure there are enough elements to extract
            continue
        
        full_name = entry[0]
        
        try:
            position_index = entry.index('Position') + 1
            company_index = entry.index('Company') + 1
            
            position = entry[position_index] if position_index < len(entry) else None
            company = entry[company_index] if company_index < len(entry) else None
            
            extracted_data.append([full_name, position, company])
        except ValueError:
            continue
    
    df = pd.DataFrame(extracted_data, columns=['Full Name', 'Position', 'Company'])
    df.to_excel(output_file, index=False)
    print(f'Data has been saved to {output_file}')



total_images = len(os.listdir(image_dir))

for i in tqdm(range(total_images), desc="Processing Images"):
    image_path = os.path.join(image_dir, f"img{i}.png")
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        new_array = text.split('\n')
        final_words.append(new_array)
    except Exception as e:
        print(f"Error processing {image_path}: {e}")

# After processing all images, call the function to extract data and save to Excel
extract_data_to_excel(final_words, output_file)
