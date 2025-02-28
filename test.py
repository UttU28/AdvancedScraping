import openai

# Set your OpenAI API key
openai.api_key = 'your-api-key'  # Replace 'your-api-key' with your actual OpenAI API key

markdown_text = """
# Define the input prompt (Markdown text or any other text you want to parse)
"""

prompt_text = """
# Heading 1
This is a paragraph with **bold text** and *italic text*.
- List item 1
- List item 2
{markdown_text}

"""

# Call the GPT-3.5 API to parse the text or convert it into another format (e.g., HTML)
response = openai.Completion.create(
    model="text-davinci-003",  # Use GPT-3.5 model
    prompt=f"Convert this Markdown into HTML:\n{prompt_text}",
    temperature=0.5,  # Controls randomness (0.5 is balanced)
    max_tokens=200  # Limit the number of tokens in the response
)

# Get and print the response text (converted HTML or other parsed format)
parsed_text = response.choices[0].text.strip()
print("Parsed Text (HTML):", parsed_text)
