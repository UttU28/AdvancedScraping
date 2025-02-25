import requests

url = "https://r.jina.ai/https://www.zoom.com/en/about/team"
headers = {
"Authorization": "Bearer jina_c41c87f796a84f8d940db9231a675248L04yxvalzHta-90dKxy5DUO7FWhh"
}

response = requests.get(url, headers=headers)

print(response.text)
