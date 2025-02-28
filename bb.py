import re
from prompts import MARKDOWN_PROMPT

def extract_team_info(markdown_text):
    team_headers = [
        r'^#{1,6}\s*Team\b', r'^#{1,6}\s*Our Team\b', r'^#{1,6}\s*Leadership\b',
        r'^#{1,6}\s*Management\b', r'^#{1,6}\s*Executives\b', r'^#{1,6}\s*Board of Directors\b'
    ]
    
    pattern = rf"({'|'.join(team_headers)})(.*?)(^#{1,6}\s|\Z)"  
    matches = re.findall(pattern, markdown_text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    
    extracted_text = "\n".join(match[1].strip() for match in matches)
    
    extracted_text = re.sub(r"!\[.*?\]\(.*?\)", "", extracted_text)  # Remove images
    extracted_text = re.sub(r"\[.*?\]\(.*?\)", "", extracted_text)  # Remove links
    extracted_text = re.sub(r"Read bio Hide bio", "", extracted_text, flags=re.IGNORECASE)  # Remove "Read bio Hide bio"

    return extracted_text.strip()

cleaned_text = extract_team_info(MARKDOWN_PROMPT)
print(cleaned_text)
