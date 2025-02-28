import ollama
from prompts import COMPLETE_PROMPT

# Select a model that performs closest to GPT-3.5
MODEL_NAME = "llama3:8b"  # Change to "mixtral" or "gemma" if needed

# Define the structured messages
messages = [
    {"role": "system", "content": "You are an AI assistant that extracts structured data ONLY from the provided Markdown content."},
    {"role": "user", "content": COMPLETE_PROMPT}
]

# Run inference using Ollama
response = ollama.chat(model=MODEL_NAME, messages=messages)

# Print the extracted structured data
print(response["message"]["content"])
