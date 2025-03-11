from googleapiclient.discovery import build
import json
import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GoogleCustomSearch:
    def __init__(self, api_key: str, search_engine_id: str):
        """
        Initialize the Google Custom Search API client.
        
        Args:
            api_key (str): Your Google API key
            search_engine_id (str): Your Custom Search Engine ID
        """
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.service = build("customsearch", "v1", developerKey=api_key)

    def search(self, query: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Perform a custom search query.
        
        Args:
            query (str): The search query
            **kwargs: Additional parameters to pass to the search
                     (e.g., num=10, start=1, etc.)
        
        Returns:
            dict: Search results or None if an error occurs
        """
        try:
            # Create a search request
            search_request = self.service.cse().list(
                q=query,
                cx=self.search_engine_id,
                **kwargs
            )

            # Execute the request
            return search_request.execute()

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None

def create_linkedin_search_query(name: str, company: str) -> str:
    """
    Create a LinkedIn search query for a person and company.
    
    Args:
        name (str): Person's name
        company (str): Company name
    
    Returns:
        str: Formatted search query
    """
    return f'site:linkedin.com/in "{name}" "{company}"'

def extract_essential_data(results: Dict[str, Any]) -> List[Dict[str, str]]:
    if 'items' not in results:
        return []
    
    return [
        {
            'title': item['title'],
            'link': item['link'],
            'snippet': item['snippet']
        }
        for item in results['items']
    ]

def save_search_results(metadata: Dict[str, str], search_results: List[Dict[str, str]], filename: str):
    # Create googleData directory if it doesn't exist
    os.makedirs('googleData', exist_ok=True)
    
    # Prepare the combined data
    combined_data = {
        'metadata': metadata,
        'search_results': search_results
    }
    
    # Save to JSON file
    filepath = os.path.join('googleData', filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
        print(f"\nResults have been saved to '{filepath}'")

def display_results(results: Dict[str, Any], query: str):
    print(f"\nSearch Results for: {query}\n")
    if 'items' in results:
        for item in results['items']:
            print(f"Title: {item['title']}")
            print(f"Link: {item['link']}")
            print(f"Snippet: {item['snippet']}")
            print("-" * 80 + "\n")
    else:
        print("No results found.")

def search_linkedin_profile(name: str, company: str, position: str, api_key: str, search_engine_id: str, output_filename: str):
    search_client = GoogleCustomSearch(api_key, search_engine_id)
    query = create_linkedin_search_query(name, company)
    print(f"\nSearching for: {query}")
    
    results = search_client.search(query, num=7)
    if results:
        essential_data = extract_essential_data(results)
        metadata = {
            'fullName': name,
            'companyName': company,
            'positionName': position
        }
        save_search_results(metadata, essential_data, output_filename)
        return True
    return False

def main():
    # Get credentials from environment variables
    API_KEY = os.getenv('GOOGLE_API_KEY')
    SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID')

    if not API_KEY or not SEARCH_ENGINE_ID:
        print("Error: Missing API credentials in environment variables")
        return

    # Create an instance of GoogleCustomSearch
    search_client = GoogleCustomSearch(API_KEY, SEARCH_ENGINE_ID)

    # Example search with LinkedIn query
    name = "Dan Kalafatas"
    company = "3Degrees"
    position = "Software Engineer"
    output_filename = "linkedin_search_results.json"
    search_linkedin_profile(name, company, position, API_KEY, SEARCH_ENGINE_ID, output_filename)

if __name__ == "__main__":
    main()
