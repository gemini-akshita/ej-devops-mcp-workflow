import os
import subprocess
import requests
from dotenv import load_dotenv
load_dotenv() 

def create_github_pr(title, description, commit_message=None, token=None):
    """
    Simple function to commit changes and create a GitHub Pull Request
    
    Args:
        title (str): PR title
        description (str): PR description
        commit_message (str, optional): Commit message. If None, uses PR title
        token (str, optional): GitHub token. If None, uses GITHUB_TOKEN env var
    
    Returns:
        str: PR URL if successful, None if failed
    """
    
    # Get GitHub token
    github_token = os.getenv('GITHUB_TOKEN') 
    if not github_token:
        print("Error: No GitHub token found. Set GITHUB_TOKEN env var or pass token parameter")
        return None
    
    try:
        # Use PR title as commit message if not provided
        if not commit_message:
            commit_message = title
        
        # Check if there are any changes to commit
        status_output = subprocess.check_output(['git', 'status', '--porcelain'], 
                                              encoding='utf-8').strip()
        
        if status_output:
            print(f"Committing changes with message: '{commit_message}'")
            
            # Add all changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Commit changes
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        else:
            print("No changes to commit")
        
        # Get current branch
        current_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                                encoding='utf-8').strip()
        
        # Get repository info from git remote
        remote_url = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], 
                                           encoding='utf-8').strip()
        
        # Parse owner/repo from URL
        if 'github.com' in remote_url:
            if remote_url.startswith('https://'):
                # https://github.com/owner/repo.git
                parts = remote_url.replace('https://github.com/', '').replace('.git', '').split('/')
            elif remote_url.startswith('git@'):
                # git@github.com:owner/repo.git
                parts = remote_url.split(':')[1].replace('.git', '').split('/')
            else:
                print("Error: Could not parse GitHub URL")
                return None
            
            owner, repo = parts[0], parts[1]
        else:
            print("Error: Not a GitHub repository")
            return None
        
        # Check if we're on a default branch (master/main)
        if current_branch in ['master', 'main']:
            print(f"You're on the default branch '{current_branch}'. Creating a feature branch...")
            
            # Create a new feature branch
            feature_branch = f"feature/{title.lower().replace(' ', '-').replace('/', '-')}"
            subprocess.run(['git', 'checkout', '-b', feature_branch], check=True)
            current_branch = feature_branch
            print(f"Created and switched to branch: {current_branch}")
        
        # Push current branch to origin
        print(f"Pushing branch '{current_branch}' to origin...")
        subprocess.run(['git', 'push', 'origin', current_branch], check=True)
        
        # Determine the base branch (what to merge into)
        base_branch = 'main'
        
        # Check if main branch exists, otherwise use master
        try:
            subprocess.check_output(['git', 'rev-parse', '--verify', 'origin/main'], 
                                   encoding='utf-8', stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            base_branch = 'master'
        
        # Create PR via GitHub API
        pr_data = {
            'title': title,
            'body': description,
            'head': current_branch,
            'base': base_branch
        }
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        url = f'https://api.github.com/repos/{owner}/{repo}/pulls'
        
        print(f"Creating PR: {title}")
        response = requests.post(url, json=pr_data, headers=headers)
        
        if response.status_code == 201:
            pr_info = response.json()
            pr_url = pr_info['html_url']
            pr_number = pr_info['number']
            
            print(f"Pull Request created successfully!")
            print(f"PR URL: {pr_url}")
            print(f"PR Number: #{pr_number}")
            
            return pr_url
        else:
            try:
                error_info = response.json()
                print(f"Failed to create PR: {error_info.get('message', 'Unknown error')}")
                print(f"Status code: {response.status_code}")
                print(f"Full error response: {error_info}")
                if 'errors' in error_info:
                    for error in error_info['errors']:
                        print(f"Error detail: {error}")
            except:
                print(f"Failed to create PR. Status code: {response.status_code}")
                print(f"Raw response: {response.text}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
        return None
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


# Example usage:
if __name__ == "__main__":
    
    # Option 2: Specify custom commit message
    pr_url = create_github_pr(
        title="Add new feature",
        description="This PR adds a new authentication feature", 
        commit_message="Implement user authentication with JWT tokens"
    )
    
    if pr_url:
        print(f"Success! Your PR is at: {pr_url}")
    else:
        print("Failed to create PR")