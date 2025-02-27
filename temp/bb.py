import ollama

response = ollama.chat(model="mistral", messages=[{"role": "user", "content": "Explain deep learning in simple terms."}])
print(response['message']['content'])
