import os
import pandas as pd
from PIL import Image
import pytesseract
from tqdm import tqdm

image_dir = 'screenShots/'
finalWords = []

totalImages = len(os.listdir(image_dir))

for i in tqdm(range(totalImages), desc="Processing Images"):
    image_path = os.path.join(image_dir, f"no_{i}.png")
    image_path = os.path.join(image_dir, f"screenshot{i}.png")
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        newArray = text.split('\n')
        finalWords.append(newArray)
    except Exception as e:
        print(f"Error processing {image_path}: {e}")

result = {}
for array in tqdm(finalWords, desc="Extracting Names and Companies"):
    for i in range(len(array) - 1):
        name = array[i].strip()
        company = array[i + 1].strip()
        
        if not name:
            continue
        if company:
            if name not in result:
                result[name] = company

df = pd.DataFrame(list(result.items()), columns=["Full Name", "Company Name"])
csv_path = 'finalData.csv'
df.to_csv(csv_path, index=False)

print(f"Data saved to {csv_path}")
