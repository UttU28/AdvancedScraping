import openai
from colorama import init, Fore, Style
from prompts import SYSTEM_PROMPT, USER_PROMPT
from dotenv import load_dotenv
import os

# Initialize colorama and load environment variables
init()
load_dotenv()

def print_status(message: str, color: str = Fore.WHITE):
    print(f"{color}{message}{Style.RESET_ALL}")

# Set your OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

def call_openai_gpt(system_prompt, user_prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        
        # Save the response to a file
        os.makedirs('openai_responses', exist_ok=True)
        output_file = 'openai_responses/response.txt'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"System Prompt:\n{system_prompt}\n\n")
            f.write(f"User Prompt:\n{user_prompt}\n\n")
            f.write(f"Response:\n{response['choices'][0]['message']['content']}")
            
        return response["choices"][0]["message"]["content"]
        
    except Exception as e:
        print_status(f"Error making OpenAI request: {str(e)}", Fore.RED)
        return None

if __name__ == "__main__":
    response = call_openai_gpt(SYSTEM_PROMPT, USER_PROMPT)
