#!/bin/bash

# Script to help test PRs for volttron-installer
# Usage: test-pr [PR-NUMBER]

set -e

if [ -z "$1" ]; then
    echo "Usage: test-pr [PR-NUMBER]"
    exit 1
fi

PR_NUMBER=$1
REPO="VOLTTRON/volttron-installer"
BRANCH="pr-$PR_NUMBER-test"

# Check if we're already in a git repo
if [ ! -d ".git" ]; then
    echo "Not in a git repository. Please run this from the root of the volttron-installer repo."
    exit 1
fi

# Check for proper SSH setup
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "SSH key not found. Checking if HTTPS should be used instead..."
    
    # Check if origin is using SSH
    CURRENT_URL=$(git remote get-url origin)
    if [[ $CURRENT_URL == git@* ]]; then
        echo "SSH key not found, but remote uses SSH. Consider using HTTPS or adding SSH keys to the container."
        echo "To convert to HTTPS, run: git remote set-url origin https://github.com/$REPO.git"
        exit 1
    fi
else
    # Ensure SSH key has correct permissions
    chmod 600 ~/.ssh/id_rsa
    echo "SSH key found with proper permissions."
fi

# Check for upstream remote, add if missing
if ! git remote | grep -q "^upstream$"; then
    echo "Adding upstream remote..."
    git remote add upstream git@github.com:$REPO.git
fi

# Make sure we're on develop and up to date
echo "Fetching latest develop branch..."
git checkout develop
git fetch upstream
git pull upstream develop

# Create a new branch for testing the PR
echo "Creating branch $BRANCH for testing..."
git checkout -b $BRANCH

# Fetch the PR
echo "Fetching PR #$PR_NUMBER..."
git fetch upstream pull/$PR_NUMBER/head:pr-$PR_NUMBER

# Merge the PR into our test branch
echo "Merging PR into test branch..."
git merge pr-$PR_NUMBER

echo ""
echo "PR $PR_NUMBER has been merged into branch $BRANCH for testing."
echo "You can now run 'pip install -r requirements.txt && pip install -e .' to update dependencies."
echo "When done, you can run 'git checkout develop && git branch -D $BRANCH pr-$PR_NUMBER' to clean up."