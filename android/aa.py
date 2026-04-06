import os
from PIL import Image

def trim_all_screenshots_left_25px():
    screenshots_dir = 'screenshots'
    if not os.path.isdir(screenshots_dir):
        print(f"Directory {screenshots_dir} does not exist.")
        return

    # Get files and filter for image files (common formats)
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
    files = [f for f in os.listdir(screenshots_dir) if f.lower().endswith(valid_extensions)]
    if not files:
        print("No image files found in screenshots directory.")
        return

    files.sort()  # Lexicographical order
    for image_filename in files:
        image_path = os.path.join(screenshots_dir, image_filename)
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                left = 25 if width > 25 else 0
                # Crop: (left, upper, right, lower)
                cropped_img = img.crop((left, 0, width, height))
                cropped_img.save(image_path)
            print(f"Trimmed 25px from the left and saved: {image_path}")
        except Exception as e:
            print(f"Failed to process image {image_filename}: {e}")

# Optionally run on execute
if __name__ == '__main__':
    trim_all_screenshots_left_25px()