#!/usr/bin/env python3
"""
Simple GitHub PR Creator with AI Analysis
"""

import json
import subprocess
import boto3
import requests
from typing import Optional, Tuple


def get_git_diff() -> str:
    """Get git diff of all changes (staged + unstaged)."""
    try:
        # Get unstaged changes with proper encoding
        unstaged_result = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, encoding='utf-8', errors='ignore', check=True
        )
        
        # Get staged changes with proper encoding
        staged_result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, encoding='utf-8', errors='ignore', check=True
        )
        
        # Combine both
        unstaged_changes = unstaged_result.stdout or ""
        staged_changes = staged_result.stdout or ""
        all_changes = unstaged_changes + staged_changes
        
        # Debug: print what we found
        print(f"Debug - Unstaged changes length: {len(unstaged_changes)}")
        print(f"Debug - Staged changes length: {len(staged_changes)}")
        print(f"Debug - Total changes length: {len(all_changes)}")
        
        return all_changes.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
        return ""


def get_current_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, encoding='utf-8', errors='ignore', check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "feature-branch"


def analyze_with_bedrock(diff: str) -> Tuple[str, str]:
    """Analyze diff using AWS Bedrock Claude 3 Haiku."""
    if len(diff) > 10000:
        diff = diff[:10000] + "\n... (truncated)"
    
    prompt = f"""Analyze this git diff and provide:
1. Short commit message (max 50 chars)
2. Brief PR description (2-3 sentences)

Diff:
{diff}

Respond in JSON: {{"summary": "...", "description": "..."}}"""
    
    try:
        # Use environment variables for AWS credentials
        client = boto3.client('bedrock-runtime', region_name='ap-south-1')
        
        response = client.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['content'][0]['text']
        
        try:
            parsed = json.loads(content)
            return parsed["summary"], parsed["description"]
        except:
            return "Update code", "Code changes made"
            
    except Exception as e:
        print(f"AI analysis failed: {e}")
        return "Update code", "Code changes made"


def create_pr(token: str, owner: str, repo: str, title: str, body: str, 
              head: str, base: str = "main") -> Optional[str]:
    """Create GitHub pull request."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    
    response = requests.post(
        url,
        headers={"Authorization": f"token {token}"},
        json={
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
    )
    
    if response.status_code == 201:
        return response.json()["html_url"]
    else:
        print(f"Failed to create PR: {response.text}")
        return None


def main():
    """Main function to create PR with AI analysis."""
    
    REPO_OWNER = "gemini-akshita"
    REPO_NAME = "ej-devops-mcp-workflow"
    BASE_BRANCH = "test"
    
    # Get diff and analyze
    print("🔍 Getting git diff...")
    diff = get_git_diff()
    
    if not diff:
        print("❌ No changes found")
        return
    
    print("🤖 Analyzing with AI...")
    summary, description = analyze_with_bedrock(diff)
    
    # First commit the changes
    print("📝 Committing changes...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", summary], check=True)
        print("✅ Changes committed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to commit: {e}")
        return
    
    # Create PR
    current_branch = get_current_branch()
    print(f"🚀 Creating PR: {summary}")
    
    pr_url = create_pr(
        GITHUB_TOKEN,
        REPO_OWNER,
        REPO_NAME,
        summary,
        description,
        current_branch,
        BASE_BRANCH
    )
    
    if pr_url:
        print(f"✅ PR created: {pr_url}")
    else:
        print("❌ Failed to create PR")


if __name__ == "__main__":
    main()