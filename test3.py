import os
import requests
import json
import subprocess
from requests.auth import HTTPBasicAuth
from typing import Dict, Any
import httpx
from mcp.server.fastmcp import FastMCP



def get_default_branch():
    """Get the default branch (main or master)"""
    try:
        result = subprocess.run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip().split('/')[-1]
    except:
        for branch in ['main', 'master']:
            try:
                subprocess.run(['git', 'rev-parse', '--verify', f'origin/{branch}'], 
                             capture_output=True, check=True)
                return branch
            except:
                continue
        return 'main'

@mcp.tool()
async def create_github_pr(title: str, description: str, branch: str, base_branch: str = None) -> Dict[str, Any]:
    """Create a GitHub Pull Request with detailed error handling"""
    
    try:
        parts = GITHUB_REPO_URL.replace('https://github.com/', '').replace('.git', '').split('/')
        if len(parts) < 2:
            return {"success": False, "error": "Invalid repository URL format"}
            
        owner, repo = parts[0], parts[1]
        
        if not base_branch:
            base_branch = get_default_branch()
        
        # Check if branch exists remotely
        try:
            result = subprocess.run(
                ['git', 'ls-remote', '--heads', 'origin', branch], 
                capture_output=True, text=True, check=True
            )
            if not result.stdout.strip():
                return {
                    "success": False, 
                    "error": f"Branch '{branch}' not found on remote. Please push the branch first."
                }
        except subprocess.CalledProcessError:
            return {
                "success": False, 
                "error": f"Could not verify branch '{branch}' exists on remote"
            }
        
        pr_data = {
            'title': title.strip(),
            'body': description.strip(),
            'head': branch,
            'base': base_branch
        }
        
        headers = {
            'Authorization': f'Bearer {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'MCP-Server/1.0'
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'https://api.github.com/repos/{owner}/{repo}/pulls',
                json=pr_data,
                headers=headers
            )
            
        if response.status_code == 201:
            pr_info = response.json()
            return {
                "success": True,
                "pr_url": pr_info['html_url'],
                "pr_number": pr_info['number'],
                "title": pr_info['title'],
                "branch": branch,
                "base_branch": base_branch
            }
        else:
            try:
                error_info = response.json()
                error_details = error_info.get('errors', [])
                error_message = error_info.get('message', 'Unknown error')
                
                detailed_error = f"GitHub API Error ({response.status_code}): {error_message}"
                if error_details:
                    detailed_error += f"\nDetails: {error_details}"
                
                return {
                    "success": False,
                    "error": detailed_error,
                    "status_code": response.status_code,
                    "pr_data": pr_data
                }
            except:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code
                }
            
    except Exception as e:
        return {
            "success": False, 
            "error": f"Unexpected error: {str(e)}",
            "pr_data": locals().get('pr_data', {})
        }

@mcp.prompt("analyze_changes")
def analyze_changes_prompt() -> str:
    """MCP Prompt: Analyze git changes, commit, push, and prepare for PR creation"""
    return """
    Complete git workflow analysis and preparation - Execute ALL steps automatically:

    STEP 1: Analyze Changes
    1. Run: git status --porcelain
    2. Run: git diff --name-status  
    3. Identify modified, added, deleted, untracked files
    4. Review file diffs to understand functionality changes

    STEP 2: Automatically Execute Git Commands
    1. Run: git add .
    2. Generate meaningful commit message based on changes:
       - If jira-related files: "Add Jira integration tools"
       - If github/pr files: "Add GitHub PR creation tools" 
       - If .py files: "Update MCP server tools"
       - Default: "Update project files"
    3. Get current branch: git rev-parse --abbrev-ref HEAD
    4. If on main/master, create feature branch:
       - Format: feature/[change-summary]-[timestamp]
       - Run: git checkout -b [branch_name]
    5. Run: git commit -m "[commit_message]"
    6. Ensure remote: git remote get-url origin
       - If different from repo URL: git remote set-url origin [GITHUB_REPO_URL]
       - If no remote: git remote add origin [GITHUB_REPO_URL]
    7. Run: git push -u origin [branch_name]
    8. Verify branch on remote: git ls-remote --heads origin [branch_name]

    STEP 3: Pre-PR Validation Checklist
    - ✅ Branch pushed to GitHub remote
    - ✅ GitHub token has PR creation permissions  
    - ✅ Repository URL matches configuration
    - ✅ Base branch (main/master) exists
    - ✅ Branch name follows feature/* convention

    STEP 4: Generate Analysis Output
    Return JSON with all information:
    {
        "title": "4-6 word change summary",
        "description": "2-3 sentences explaining changes and purpose",
        "files_changed": ["file1.py", "file2.js"],
        "change_type": "feature|bugfix|refactor|docs",
        "branch_name": "feature/descriptive-name-timestamp",
        "commit_message": "Clear descriptive commit message", 
        "git_commands_executed": ["git add .", "git commit -m ...", "git push ..."],
        "ready_for_pr": true,
        "git_status": "committed_and_pushed",
        "remote_verified": true
    }

    Execute ALL git operations automatically - no user confirmation needed.
    Ensure branch is completely ready for create_github_pr tool usage.
    """

@mcp.prompt("create_pr")
def create_pr_prompt() -> str:
    """MCP Prompt: Create GitHub Pull Request using analyzed changes"""
    return """
    Create a GitHub Pull Request using the create_github_pr tool:

    1. Use the title and description from the analyzed changes
    2. Specify the current branch name where changes were pushed
    3. Optionally specify the base branch (defaults to main/master)

    Example usage:
    - title: Use the generated title from change analysis
    - description: Expand the description with technical details and context
    - branch: The feature branch containing your changes
    - base_branch: Target branch (usually main/master)

    The tool will automatically:
    - Parse repository information from GITHUB_REPO_URL
    - Create the PR with proper authentication
    - Return the PR URL and number for reference
    """

@mcp.prompt("create_jira_ticket")  
def create_jira_ticket_prompt() -> str:
    """MCP Prompt: Create Jira ticket using analyzed changes"""
    return """
    Create a Jira ticket using the create_jira_ticket tool:

    Parameters needed:
    - summary: A concise title (4-6 words) describing the task or change
    - description: A brief explanation of what needs to be done or what was completed

    The tool will:
    - Create a Task type issue in the configured Jira project
    - Use the provided summary as the ticket title
    - Format the description in Jira's document format
    - Return the ticket key and URL for tracking

    Use information from change analysis to populate meaningful summary and description.
    """

@mcp.tool()
def commit_and_push_branch(commit_message: str = None, branch_name: str = None) -> Dict[str, Any]:
    """Stage all changes, commit, create branch if needed, and push to remote"""
    try:
        # Check if there are changes
        status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                     capture_output=True, text=True, check=True)
        
        if not status_result.stdout.strip():
            return {"success": False, "error": "No changes to commit"}
        
        # Get current branch
        current_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                      capture_output=True, text=True, check=True).stdout.strip()
        
        # Generate commit message if not provided
        if not commit_message:
            # Analyze changes for commit message
            diff_result = subprocess.run(['git', 'diff', '--name-status'], 
                                       capture_output=True, text=True)
            changes = diff_result.stdout.strip()
            
            if "jira" in changes.lower():
                commit_message = "Add Jira integration tools"
            elif "github" in changes.lower() or "pr" in changes.lower():
                commit_message = "Add GitHub PR creation tools"
            elif ".py" in changes:
                commit_message = "Update MCP server tools"
            else:
                commit_message = "Update project files"
        
        # Generate branch name if not provided and on main/master
        if not branch_name:
            if current_branch in ['main', 'master']:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                safe_message = commit_message.lower().replace(' ', '-')[:30]
                branch_name = f"feature/{safe_message}-{timestamp}"
            else:
                branch_name = current_branch
        
        commands_executed = []
        
        # Stage all changes
        subprocess.run(['git', 'add', '.'], check=True)
        commands_executed.append("git add .")
        
        # Create branch if needed
        if current_branch in ['main', 'master'] and branch_name != current_branch:
            subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
            commands_executed.append(f"git checkout -b {branch_name}")
        
        # Commit changes
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        commands_executed.append(f'git commit -m "{commit_message}"')
        
        # Ensure remote is set
        # try:
        #     remote_url = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
        #                               capture_output=True, text=True, check=True).stdout.strip()
        #     if remote_url != GITHUB_REPO_URL:
        #         subprocess.run(['git', 'remote', 'set-url', 'origin', GITHUB_REPO_URL], check=True)
        #         commands_executed.append(f"git remote set-url origin {GITHUB_REPO_URL}")
        # except subprocess.CalledProcessError:
        #     subprocess.run(['git', 'remote', 'add', 'origin', GITHUB_REPO_URL], check=True)
        #     commands_executed.append(f"git remote add origin {GITHUB_REPO_URL}")
        
        # Push to remote
        subprocess.run(['git', 'push', '-u', 'origin', branch_name], check=True)
        commands_executed.append(f"git push -u origin {branch_name}")
        
        # Verify branch exists on remote
        remote_check = subprocess.run(['git', 'ls-remote', '--heads', 'origin', branch_name], 
                                    capture_output=True, text=True, check=True)
        
        if not remote_check.stdout.strip():
            return {
                "success": False,
                "error": f"Branch {branch_name} was not found on remote after push"
            }
        
        return {
            "success": True,
            "branch_name": branch_name,
            "commit_message": commit_message,
            "commands_executed": commands_executed,
            "remote_verified": True,
            "message": f"Successfully committed and pushed to branch: {branch_name}"
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"Git operation failed: {e}",
            "stderr": e.stderr if hasattr(e, 'stderr') else None,
            "commands_executed": commands_executed if 'commands_executed' in locals() else []
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
    """Debug GitHub repository and branch setup"""
    
    debug_info = {
        "repo_url": GITHUB_REPO_URL,
        "current_branch": None,
        "remote_branches": [],
        "git_remote": None,
        "token_valid": None,
        "issues": []
    }
    
    try:
        # Get current branch
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                              capture_output=True, text=True, check=True)
        debug_info["current_branch"] = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        debug_info["issues"].append(f"Could not get current branch: {e}")
    
    try:
        # Get remote URL
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                              capture_output=True, text=True, check=True)
        debug_info["git_remote"] = result.stdout.strip()
        
        if debug_info["git_remote"] != GITHUB_REPO_URL:
            debug_info["issues"].append(f"Git remote mismatch: {debug_info['git_remote']} != {GITHUB_REPO_URL}")
    except subprocess.CalledProcessError as e:
        debug_info["issues"].append(f"No git remote found: {e}")
    
    try:
        # Get remote branches
        result = subprocess.run(['git', 'ls-remote', '--heads', 'origin'], 
                              capture_output=True, text=True, check=True)
        branches = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                branch_name = line.split('/')[-1]
                branches.append(branch_name)
        debug_info["remote_branches"] = branches
    except subprocess.CalledProcessError as e:
        debug_info["issues"].append(f"Could not list remote branches: {e}")
    
    # Check if current branch exists on remote
    if debug_info["current_branch"] and debug_info["remote_branches"]:
        if debug_info["current_branch"] not in debug_info["remote_branches"]:
            debug_info["issues"].append(f"Current branch '{debug_info['current_branch']}' not pushed to remote")
    
    # Validate GitHub token format
    if not GITHUB_TOKEN.startswith('ghp_') and not GITHUB_TOKEN.startswith('github_pat_'):
        debug_info["issues"].append("GitHub token format may be invalid")
    
# if __name__ == "__main__":
#     mcp.run(transport="sse")