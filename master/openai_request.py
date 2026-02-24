import os
from pathlib import Path

from dotenv import load_dotenv
import openai
from prompts import SYSTEM_PROMPT, USER_PROMPT

load_dotenv(Path(__file__).resolve().parent / ".env")

openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "sk-proj-REPLACE_WITH_YOUR_KEY"
openai.api_key = OPENAI_API_KEY


def call_openai_gpt(system_prompt, user_prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        content = response["choices"][0]["message"]["content"]
        os.makedirs("openai_responses", exist_ok=True)
        with open("openai_responses/response.txt", "w", encoding="utf-8") as f:
            f.write(f"System Prompt:\n{system_prompt}\n\n")
            f.write(f"User Prompt:\n{user_prompt}\n\n")
            f.write(f"Response:\n{content}")
        return content
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    call_openai_gpt(SYSTEM_PROMPT, USER_PROMPT)
