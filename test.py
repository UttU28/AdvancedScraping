import requests

# Define the URL and headers
url = 'http://127.0.0.1:3000/https://google.com'  # Updated URL to match Docker container endpoint
headers = {
    'X-Respond-With': 'markdown'  # You can change this to 'html', 'text', 'screenshot', or 'pageshot'
}

# Make the POST request
response = requests.post(url, headers=headers)

# Print the response
print(response.text)
