"""
Chrome/Selenium helpers and CSV reading for verifyEvents.
Loads .env from verifyEvents folder only.
"""
import csv
import os
import subprocess
import socket
from pathlib import Path
from time import sleep

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

load_dotenv(Path(__file__).resolve().parent / ".env")

CRAWLER_DIR = Path(__file__).resolve().parent
EVENTS_CSV_PATH = CRAWLER_DIR / "source.csv"

chromeDriverPath = os.getenv("CHROME_DRIVER_PATH")
chromeAppPath = os.getenv("CHROME_APP_PATH")
chromeUserDataDir = os.getenv("APPLYING_CHROME_DIR")
debuggingPort = os.getenv("APPLYING_PORT")


def isPortInUse(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", int(port)))
            return False
        except socket.error:
            return True


def startChrome(debuggingPort, userDataDir, chromeAppPath):
    if isPortInUse(debuggingPort):
        return None
    p = subprocess.Popen([
        chromeAppPath,
        f"--remote-debugging-port={debuggingPort}",
        f"--user-data-dir={userDataDir}",
    ])
    sleep(2)
    return p


def setupChromeDriver(debuggingPort, chromeDriverPath):
    options = Options()
    options.add_experimental_option("debuggerAddress", f"localhost:{debuggingPort}")
    options.add_argument(f"webdriver.chrome.driver={chromeDriverPath}")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(options=options)


def cleanupChrome(driver, chromeApp):
    driver.quit()
    if chromeApp:
        chromeApp.terminate()
        try:
            chromeApp.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chromeApp.kill()
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/FI", f"COMMANDLINE eq *{debuggingPort}*", "/IM", "chrome.exe"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.run(
                    ["pkill", "-f", f"chrome.*--remote-debugging-port={debuggingPort}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass


def read_events_csv(csv_path=None):
    path = csv_path or EVENTS_CSV_PATH
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def print_events_csv(csv_path=None):
    path = csv_path or EVENTS_CSV_PATH
    if not path.exists():
        print(f"CSV not found: {path}")
        return
    rows = read_events_csv(path)
    print(f"Total rows: {len(rows)}\n")
    for i, row in enumerate(rows, 1):
        print(f"--- Row {i} ---")
        for k, v in row.items():
            print(f"  {k}: {v}")
        print()
    return rows


if __name__ == "__main__":
    print_events_csv()
