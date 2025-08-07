from ppadb.client import Client as AdbClient
from PIL import Image
import pytesseract
from time import sleep

client = AdbClient(host="127.0.0.1", port=5037)

def connect_device():
    devices = client.devices()
    if not devices:
        print("No devices connected.")
        return None
    return devices[0] 

def cropTheImage(imageName):
    image = Image.open(imageName)
    cropped_image = image.crop((0, 380, 720, 1200))
    cropped_image.save(imageName)

def take_screenshot(device, imageName):
    screenshot = device.screencap()
    with open(imageName, "wb") as f:
        f.write(screenshot)
    # cropTheImage(imageName)


def main():
    device = connect_device()
    if not device:
        return
    imageCounter = 0
    # while True:
        # imageName = f"screenShots/img{imageCounter}.png"
        # imageCounter += 1
        # take_screenshot(device, imageName)
    device.shell("input swipe 500 900 500 100 500")
        # data = pytesseract.image_to_string(imageName)
        # print(data.split("\n"))
        # sleep(0.4)
        # if imageCounter == 28*1: exit()

    

if __name__ == "__main__":
    main()

# 380, 1200