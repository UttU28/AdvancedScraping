import ollama
import pandas as pd
import json
import sys
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Logging Functions

def printSuccess(message):
    print(f"{Fore.GREEN}\u2713 {message}{Style.RESET_ALL}")

def printError(message):
    print(f"{Fore.RED}\u2717 {message}{Style.RESET_ALL}")

def printInfo(message):
    print(f"{Fore.CYAN}\u2139 {message}{Style.RESET_ALL}")

def printWarning(message):
    print(f"{Fore.YELLOW}\u26A0 {message}{Style.RESET_ALL}")

# Function to Extract Data from Markdown

def extractInfoFromMarkdown(markdownText):
    printInfo("Starting markdown extraction...")
    
    prompt = f"""
    You are an AI assistant that extracts structured data from Markdown content.  
    Your task is to extract the following details:  

    - Full Name  
    - Company Name  
    - Position  
    - LinkedIn URL  
    - Other URLs  

    ### Instructions  
    1. Return the output in JSON format with keys: fullName, company, position, linkedin, and otherUrls.  
    2. If a field is not found, return an empty string ("") instead of incorrect or assumed values.  
    3. Only use the information explicitly mentioned in the Markdown—do not make assumptions.  

    ### Markdown Content:
    {markdownText}

    ### Expected JSON Output Format:  
    ```json
    {{
      "fullName": "John Doe",
      "company": "Acme Corp",
      "position": "Software Engineer",
      "linkedin": "https://linkedin.com/in/johndoe",
      "otherUrls": ["https://johndoe.dev"]
    }}
    ```
    """

    try:
        # response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': 'hi'}])
        response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
        print(1234567890)
        print(response['message']['content'])
        extractedData = json.loads(response['message']['content'])
        
        requiredKeys = ["fullName", "company", "position", "linkedin", "otherUrls"]
        for key in requiredKeys:
            if key not in extractedData:
                extractedData[key] = ""

        printSuccess("Successfully extracted data from markdown.")
        return extractedData

    except json.JSONDecodeError:
        printError("Failed to parse JSON response from Ollama.")
        return None
    except Exception as e:
        printError(f"Unexpected error during extraction: {str(e)}")
        return None

# Function to Save Data to Excel

def saveToExcel(data, filename="extractedData.xlsx"):
    try:
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine='openpyxl')
        printSuccess(f"Data successfully saved to {filename}")
    except Exception as e:
        printError(f"Failed to save Excel file: {str(e)}")

# Main Execution Flow

def main():
    try:
        printInfo("Reading result.json file...")
        with open('result.json', 'r', encoding='utf-8') as f:
            resultData = json.load(f)

        if "data" not in resultData or "markdown" not in resultData["data"]:
            printWarning("Invalid JSON format: Expected 'data' -> 'markdown' key.")
            sys.exit(1)

        printInfo("Extracting markdown content from JSON...")
        markdownContent = resultData['data']['markdown']

        if not markdownContent.strip():
            printWarning("No markdown content found in result.json.")
            sys.exit(1)

        extractedInfo = extractInfoFromMarkdown(markdownContent)

        if extractedInfo:
            saveToExcel([extractedInfo])
            printSuccess("Successfully processed result.json and saved extracted data!")
        else:
            printError("No valid data could be extracted from the markdown content.")

    except FileNotFoundError:
        printError("Error: result.json file not found.")
    except json.JSONDecodeError:
        printError("Error: Invalid JSON format in result.json.")
    except KeyError as e:
        printError(f"Error: Missing expected key in JSON: {e}")
    except Exception as e:
        printError(f"Unexpected error occurred: {str(e)}")

# Run the Main Function
if __name__ == "__main__":
    main()
