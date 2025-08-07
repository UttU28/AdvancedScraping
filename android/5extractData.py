import os
import pandas as pd
from PIL import Image
import pytesseract
from tqdm import tqdm

# Main script
# image_dir = 'moreImages/'  # Use your preferred directory
image_dir = 'lessImages/'  # Use your preferred directory
final_words = []
output_file = 'aa.xlsx'

total_images = len(os.listdir(image_dir))

for i in tqdm(range(total_images), desc="Processing Images"):
    image_path = os.path.join(image_dir, f"img{i}.png")
    try:
        image = Image.open(image_path)
        image = image.rotate(180)
        text = pytesseract.image_to_string(image)
        new_array = text.split('\n')
        final_words.append(new_array)
    except Exception as e:
        print(f"Error processing {image_path}: {e}")


print(final_words)
# unique_entries = set()
# for sublist in final_words:
#     entry = []
#     for item in sublist:
#         if item == '':
#             if len(entry) == 3:
#                 unique_entries.add(tuple(entry))
#             entry = []
#         else:
#             entry.append(item)

#     if len(entry) == 3:
#         unique_entries.add(tuple(entry))

# final_data = [
#     {"Full Name": name, "Position": position, "Company Name": company}
#     for name, position, company in unique_entries
# ]
# df = pd.DataFrame(final_data)

# df.to_excel(output_file, index=False)

# print(f"Data has been saved to {output_file}.")
