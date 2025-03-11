import json
import requests
import time
from typing import Optional, Dict, Any
from tqdm import tqdm
from colorama import init, Fore, Style
from dotenv import load_dotenv
import os

# Initialize colorama and load environment variables
init()
load_dotenv()

# Hunter.io API configuration
hunterApiKey = os.getenv('HUNTER_API_KEY')
if not hunterApiKey:
    raise ValueError("Hunter.io API key not found in environment variables")
    
hunterApiUrl = "https://api.hunter.io/v2/email-finder"
rateLimitPerSecond = 15
rateLimitPerMinute = 500

def splitName(fullName):
    # Common titles and suffixes to handle
    titles = ['Dr.', 'Dr', 'Mr.', 'Mr', 'Mrs.', 'Mrs', 'Ms.', 'Ms', 'Prof.', 'Prof', 'Professor']
    suffixes = ['Jr.', 'Jr', 'Sr.', 'Sr', 'III', 'II', 'IV', 'V', 'PhD', 'Ph.D.', 'MD', 'M.D.', 'MBA', 'M.B.A.']
    
    # Remove any titles from the beginning
    nameParts = fullName.split()
    while nameParts and nameParts[0] in titles:
        nameParts.pop(0)
    
    # Remove any suffixes from the end
    while nameParts and nameParts[-1] in suffixes:
        nameParts.pop()
    
    if len(nameParts) >= 2:
        firstName = nameParts[0]
        lastName = ' '.join(nameParts[1:])
    else:
        firstName = fullName
        lastName = ""
    
    return firstName, lastName

def findEmail(domain, firstName, lastName):
    """
    Find email using Hunter.io API with rate limiting
    """
    try:
        # Rate limiting: Sleep for 1/15th of a second to respect rate limit
        time.sleep(1/rateLimitPerSecond)
        
        params = {
            'domain': domain,
            'first_name': firstName,
            'last_name': lastName,
            'api_key': hunterApiKey
        }
        
        response = requests.get(hunterApiUrl, params=params)
        
        # Handle specific error cases
        if response.status_code == 400:
            errorData = response.json()
            errorType = errorData.get('errors', [{}])[0].get('code')
            if errorType == 'claimed_email':
                return {'error': 'claimed_email'}
            elif errorType == 'invalid_domain':
                return {'error': 'invalid_domain'}
            else:
                return {'error': errorData.get('errors', [{}])[0].get('message')}
                
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}

def saveToJson(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def processAllEntries():
    try:
        # Read the consolidated LinkedIn data
        with open('consolidated_linkedin_data.json', 'r', encoding='utf-8') as f:
            linkedinData = json.load(f)
            
        if not linkedinData:
            print(f"{Fore.RED}No data found in consolidated JSON file!{Style.RESET_ALL}")
            return
            
        # Read the company domains data
        with open('company_domains.json', 'r', encoding='utf-8') as f:
            companyDomains = json.load(f)
            
        totalEntries = len(linkedinData)
        foundEmails = 0
        skippedEntries = 0
        invalidDomains = 0
        claimedEmails = 0
        errors = 0
        
        print(f"{Fore.CYAN}Processing {totalEntries} entries...{Style.RESET_ALL}")
        
        for entry in tqdm(linkedinData, desc="Finding emails"):
            if 'email_data' in entry and entry['email_data']:
                skippedEntries += 1
                continue
                
            companyName = entry['Company Name']
            domain = companyDomains.get(companyName, "Domain not found")
            fullName = entry['Full Name']
            firstName, lastName = splitName(fullName)
            
            entry.update({
                'First Name': firstName,
                'Last Name': lastName,
                'Company URL': domain,
                'email_data': {}
            })
            
            # Find email if we have a valid domain
            if domain != "Domain not found":
                emailResult = findEmail(domain, firstName, lastName)
                
                if emailResult and 'data' in emailResult:
                    data = emailResult['data']
                    entry['email_data'].update({
                        'email': data.get('email'),
                        'score': data.get('score'),
                        'verification_status': data.get('verification', {}).get('status')
                    })
                    foundEmails += 1
                    saveToJson(linkedinData, 'consolidated_linkedin_data.json')
                elif emailResult.get('error') == 'claimed_email':
                    entry['email_data']['error'] = 'claimed_email'
                    claimedEmails += 1
                    saveToJson(linkedinData, 'consolidated_linkedin_data.json')
                elif emailResult.get('error') == 'invalid_domain':
                    entry['email_data']['error'] = 'invalid_domain'
                    invalidDomains += 1
                    saveToJson(linkedinData, 'consolidated_linkedin_data.json')
                else:
                    entry['email_data']['error'] = emailResult.get('error')
                    errors += 1
                    saveToJson(linkedinData, 'consolidated_linkedin_data.json')
        
        print(f"\n{Fore.GREEN}Processing Complete!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Summary:{Style.RESET_ALL}")
        print(f"Total entries: {totalEntries}")
        print(f"Skipped (already processed): {skippedEntries}")
        print(f"Emails found: {foundEmails}")
        print(f"Invalid domains: {invalidDomains}")
        print(f"Claimed emails: {claimedEmails}")
        print(f"Other errors: {errors}")
        
    except FileNotFoundError as e:
        print(f"{Fore.RED}Error: File not found! {str(e)}{Style.RESET_ALL}")
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error: Invalid JSON file!{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}An error occurred: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    processAllEntries() 