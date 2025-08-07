import requests

# List of paths
aa = [
    '/usa/texas/dallas/', '/usa/texas/houston/', '/usa/texas/san-antonio/',
    '/usa/texas/el-paso/', '/usa/texas/amarillo/', '/usa/texas/austin/',
    '/usa/texas/mcallen/', '/usa/texas/bryan/', '/usa/texas/the-woodlands/',
    '/usa/texas/lubbock/', '/usa/texas/nacogdoches/', '/usa/texas/tyler/',
    '/usa/texas/laredo/', '/usa/texas/waco/', '/usa/texas/abilene/',
    '/usa/texas/harlingen/', '/usa/texas/wichita-falls/', 
    '/usa/texas/corpus-christi/', '/usa/texas/eagle-pass/', 
    '/usa/texas/fort-stockton/', '/usa/texas/montgomery-tx/', 
    '/usa/texas/pecos/', '/usa/texas/san-angelo/', '/usa/texas/stratford/'
]

# Base URL
baseURL = "https://www.datacentermap.com"

# Loop through each path, make a request, and print the HTML content
for path in aa:
    url = f"{baseURL}{path}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        print(f"Content for {url}:")
        print(response)  # Print first 500 characters of the HTML content
        print("\n" + "="*50 + "\n")
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
