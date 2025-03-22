import json
import re
import os
import time
from colorama import init, Fore, Style
from tqdm import tqdm
import openai
from prompts import SYSTEM_PROMPT, USER_PROMPT
from dotenv import load_dotenv

# Initialize colorama and load environment variables
init()
load_dotenv()

# Set OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

if not openai.api_key:
    raise ValueError("OpenAI API key not found in environment variables")

def callOpenaiGpt(systemPrompt, userPrompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": systemPrompt},
                {"role": "user", "content": userPrompt}
            ],
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        os.makedirs('openai_responses', exist_ok=True)
        outputFile = 'openai_responses/response.txt'

        with open(outputFile, 'w', encoding='utf-8') as f:
            f.write(f"System Prompt:\n{systemPrompt}\n\n")
            f.write(f"User Prompt:\n{userPrompt}\n\n")
            f.write(f"Response:\n{response['choices'][0]['message']['content']}")

        return response["choices"][0]["message"]["content"]

    except Exception as e:
        printStatus(f"Error making OpenAI request: {str(e)}", Fore.RED)
        return None

def printStatus(message: str, color: str = Fore.WHITE):
    print(f"{color}{message}{Style.RESET_ALL}")

def extractLinkedinUrl(text):
    pattern = r'https://(?:www\.)?linkedin\.com/in/[^"\s]+'
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return None

def processEntry(entry):
    if 'viewed' not in entry['metadata']:
        entry['metadata']['viewed'] = True

        userPrompt = USER_PROMPT.replace("{json_input}", json.dumps(entry, indent=2))
        response = callOpenaiGpt(SYSTEM_PROMPT, userPrompt)

        if response:
            linkedinUrl = extractLinkedinUrl(response)

            if linkedinUrl:
                entry['metadata']['linkedIn'] = linkedinUrl
                return entry, True

        return entry, False
    return entry, False

def readLinkedinResults():
    try:
        directory = 'googleData'
        allFiles = [f for f in os.listdir(directory) if f.endswith('.json')]

        for file in allFiles:
            filepath = os.path.join(directory, file)
            printStatus(f"\nProcessing LinkedIn results from: {filepath}", Fore.CYAN)

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            totalEntries = len(data)
            foundCount = 0
            processedCount = 0

            if data:
                for i, entry in enumerate(tqdm(data, desc="Processing entries", unit="entry")):
                    updatedEntry, found = processEntry(entry)
                    data[i] = updatedEntry
                    if found:
                        foundCount += 1
                    processedCount += 1

                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    time.sleep(0.3)

                printStatus("\nProcessing completed!", Fore.GREEN)
                printStatus(f"Total entries in file: {totalEntries}", Fore.WHITE)
                printStatus(f"Entries processed: {processedCount}", Fore.WHITE)
                printStatus(f"LinkedIn URLs found: {foundCount}", Fore.GREEN)
                printStatus(f"LinkedIn URLs not found: {processedCount - foundCount}", Fore.YELLOW)
                printStatus(f"Success rate: {(foundCount/processedCount)*100:.1f}%", Fore.CYAN)
            else:
                printStatus("No entries found in the file.", Fore.YELLOW)

            time.sleep(2)

    except Exception as e:
        printStatus(f"An error occurred: {str(e)}", Fore.RED)

if __name__ == "__main__":
    readLinkedinResults()
