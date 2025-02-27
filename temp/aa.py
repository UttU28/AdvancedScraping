import ollama
import pandas as pd
import json
import sys
import re
import time
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
        You are an AI assistant specialized in extracting structured data from Markdown content.  
        Your task is to extract details for **each individual** mentioned in the given content, using only the information explicitly provided.

        ### Details to Extract for Each Person:  
        - **Full Name**  
        - **Position**  
        - **LinkedIn URL**  
        - **Other URLs** (any other relevant URLs associated with the person)

        ### Instructions:  
        1. **Output Format**: Return the results as a JSON array. Each element in the array should be an object with the keys `fullName`, `position`, `linkedin`, and `otherUrls`.  
        2. **Exact Data Only**: Only include information that is explicitly present in the Markdown content. **Do not guess or infer** details that aren't provided. If a specific field (e.g., LinkedIn URL or position) is not found for a person, use an empty string (`""`) for that field.  
        3. **All Individuals**: Extract details for **every person** mentioned in the content. Do not omit any individuals, and do not merge details of different people into one entry.  
        4. **No Placeholder Data**: **Do not** return the example output or any placeholder names (like "John Doe" or "Jane Smith") unless those exact names actually appear in the content. The example given is only to illustrate the format, not to be used as actual output.  
        5. **Debug Logging**: If certain details are missing or if no individuals are found:  
        - Still return a JSON array (it will be empty if no person is mentioned).  
        - After the JSON output, include a brief comment or note explaining why data is missing or why the array is empty. For example: *“No LinkedIn URL provided for Alice, so 'linkedin' is empty.”* or *“No individuals mentioned in the content, returned an empty list.”* This debug note should clarify any missing information without guessing.  

        ### Markdown Content:  
        {markdownText}

        ### Expected JSON Output Format:  
        ```json
        [
        {{
            "fullName": "John Doe",
            "position": "Software Engineer",
            "linkedin": "https://linkedin.com/in/johndoe",
            "otherUrls": ["https://johndoe.dev"]
        }},
        {{
            "fullName": "Jane Smith",
            "position": "Product Manager",
            "linkedin": "https://linkedin.com/in/janesmith",
            "otherUrls": []
        }}
        ]

    """


    try:
        start_time = time.time()
        
        response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
        print(response)
        end_time = time.time()
        printInfo(f"Ollama request completed in {end_time - start_time:.2f} seconds")
    
        rawResponse = response['message']['content']
        printInfo("Raw response received from LLM:")

        # Extract JSON content using regex
        jsonMatch = re.search(r'\[\s*\{.*\}\s*\]', rawResponse, re.DOTALL)

        if jsonMatch:
            extractedJson = jsonMatch.group(0)  # Get the matched JSON string
            extractedData = json.loads(extractedJson)  # Parse JSON
            printSuccess("Successfully extracted data from markdown.")
            return extractedData
        else:
            printError("Failed to extract a valid JSON response from Ollama.")
            return None

    except json.JSONDecodeError:
        printError("JSON Decode Error: Unable to parse JSON response.")
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
        with open('scrape_results.json', 'r', encoding='utf-8') as f:
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
            saveToExcel(extractedInfo)  # Save as a list of dictionaries
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
