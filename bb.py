import ollama

# Send a simple "hi" message to the Mistral model
response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': 'hi'}])

# Print the response from the model
print("response['message']['content']")
print(response['message']['content'])
