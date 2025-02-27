import ollama

# Override Ollama's host to ensure it connects to localhost

try:
    response = ollama.chat(
        model='llama3.2',
        messages=[{'role': 'user', 'content': 'hi'}],
    )
    print(response['message']['content'])
except Exception as e:
    print(f"Error: {e}")
