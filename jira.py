import requests
import json
from requests.auth import HTTPBasicAuth

def create_jira_ticket(summary: str, description: str) -> str:
    """Create a new Jira ticket"""
    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    
    ticket_data = {
        "fields": {
            "project": {
                "key": JIRA_PROJECT_KEY
            },
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description
                            }
                        ]
                    }
                ]
            },
            "issuetype": {
                "name": "Task"  
            }
        }
    }
    
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    print(f"Creating Jira ticket...")
    print(f"Summary: {summary}")
    
    try:
        response = requests.post(url, json=ticket_data, headers=headers, auth=auth)
        response.raise_for_status()
        
        result = response.json()
        ticket_key = result["key"]
        ticket_url = f"{JIRA_BASE_URL}/browse/{ticket_key}"
        
        print(f"Jira ticket created: {ticket_key}")
        print(f"URL: {ticket_url}")
        
        return ticket_key
        
    except requests.exceptions.HTTPError as e:
        print(f"Failed to create Jira ticket: {e}")
        print(f"Response: {response.text}")
        raise


def main():
    summary = "Review PR: Added user authentication API"
    description = "Please review the changes for the new user authentication API implementation including JWT token handling and database schema updates."
    
    ticket_key = create_jira_ticket(summary, description)
    print(f"Created ticket: {ticket_key}")


if __name__ == "__main__":
    main()