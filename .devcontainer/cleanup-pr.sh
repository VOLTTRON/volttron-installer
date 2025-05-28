#!/bin/bash

# Script to clean up after testing a PR
# Usage: cleanup-pr [PR-NUMBER]
# If PR-NUMBER is not provided, it will attempt to find the current test branch

set -e

# Function to extract PR number from branch name
function extract_pr_number() {
    local branch_name=$1
    if [[ $branch_name =~ ^pr-([0-9]+)-test$ ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi
    return 1
}

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)

# If PR number is provided as argument, use it
if [ -n "$1" ]; then
    PR_NUMBER=$1
    BRANCH="pr-$PR_NUMBER-test"
    PR_BRANCH="pr-$PR_NUMBER"
else
    # Try to extract PR number from current branch
    if PR_NUMBER=$(extract_pr_number "$CURRENT_BRANCH"); then
        BRANCH="$CURRENT_BRANCH"
        PR_BRANCH="pr-$PR_NUMBER"
    else
        echo "Error: Not on a PR test branch and no PR number provided."
        echo "Usage: cleanup-pr [PR-NUMBER]"
        echo "Current branch: $CURRENT_BRANCH"
        exit 1
    fi
fi

echo "Cleaning up PR #$PR_NUMBER (branches: $BRANCH and $PR_BRANCH)"

# Check if we need to switch branches
if [ "$CURRENT_BRANCH" != "develop" ] && [ "$CURRENT_BRANCH" == "$BRANCH" ]; then
    echo "Switching to develop branch..."
    git checkout develop
fi

# Make sure we're on develop before deleting branches
if [ "$(git branch --show-current)" != "develop" ]; then
    git checkout develop
fi

# Check if branches exist before trying to delete them
PR_TEST_EXISTS=$(git branch | grep -q " $BRANCH$" && echo "yes" || echo "no")
PR_BRANCH_EXISTS=$(git branch | grep -q " $PR_BRANCH$" && echo "yes" || echo "no")

if [ "$PR_TEST_EXISTS" == "yes" ]; then
    echo "Deleting branch $BRANCH..."
    git branch -D "$BRANCH"
else
    echo "Branch $BRANCH not found, skipping deletion."
fi

if [ "$PR_BRANCH_EXISTS" == "yes" ]; then
    echo "Deleting branch $PR_BRANCH..."
    git branch -D "$PR_BRANCH"
else
    echo "Branch $PR_BRANCH not found, skipping deletion."
fi

# Pull the latest changes from upstream
echo "Pulling latest changes from upstream..."
if git remote | grep -q "^upstream$"; then
    git pull upstream develop
else
    git pull origin develop
fi

echo "Cleanup complete. Current branch: $(git branch --show-current)"