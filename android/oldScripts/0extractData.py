from ppadb.client import Client as AdbClient
from time import sleep
from PIL import Image
import pytesseract
import os

def cropTheImage(imageName):
    image = Image.open(imageName)
    cropped_image = image.crop((130, 175 + 80, 720, 1410))
    cropped_image.save(imageName)
    print(f"Cropped image saved as {imageName}")

def delete_old_images(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Deleted old image: {filename}")

screenshot_folder = "screenShots"
delete_old_images(screenshot_folder)

client = AdbClient(host="127.0.0.1", port=5037)
devices = client.devices()

if len(devices) == 0:
    print("No devices found")
    exit()

device = devices[0]
print(f"Connected to {device}")

device_info = device.shell("getprop ro.product.model")
print(f"Device model: {device_info}")

counter = 0
while True:
    device.shell("screencap -p /sdcard/screenshot.png")
    imageName = f"{screenshot_folder}/no_{counter}.png"
    device.pull("/sdcard/screenshot.png", imageName)
    cropTheImage(imageName)
    counter += 1
    sleep(0.4)
    device.shell("input swipe 500 940 500 100 1000")
    break
