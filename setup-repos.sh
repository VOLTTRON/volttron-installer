#!/bin/bash
# Repository Setup Script for VOLTTRON Installer
# This script automates the cloning of all required dependencies

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}VOLTTRON Installer - Repo Setup${NC}"
echo "========================================"
echo ""

# Configuration
GITHUB_USERNAME="${GITHUB_USERNAME:-riley206-pnnl}"
# Default to parent directory of current script if WORKSPACE_DIR not set
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_DIR="${WORKSPACE_DIR:-$(dirname "$SCRIPT_DIR")}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  GitHub Username: $GITHUB_USERNAME"
echo "  Workspace: $WORKSPACE_DIR"
echo "  Branches:"
echo "    - volttron-installer: develop"
echo "    - eclipse-bacnet-scan-tool: develop"
echo "    - lib-protocol-proxy-fixed: bus_adapter_changes"
echo "    - lib-protocol-proxy-bacnet-fixed: merge_of_rileys_code_and_latest_changes"
echo ""

# Ensure we are in the workspace directory
mkdir -p "$WORKSPACE_DIR"
cd "$WORKSPACE_DIR"

# Clone repositories with their specific branches
declare -A repos
repos["lib-protocol-proxy-fixed"]="bus_adapter_changes"
repos["lib-protocol-proxy-bacnet-fixed"]="merge_of_rileys_code_and_latest_changes"
repos["eclipse-bacnet-scan-tool"]="develop"

for repo in "${!repos[@]}"; do
    branch="${repos[$repo]}"
    if [ -d "$repo" ]; then
        echo -e "${YELLOW}Directory $repo already exists...${NC}"
        # Check branch
        cd "$repo"
        current_branch=$(git rev-parse --abbrev-ref HEAD)
        if [ "$current_branch" != "$branch" ]; then
            echo -e "${RED}  Warning: $repo is on branch '$current_branch', expected '$branch'.${NC}"
        else
            echo -e "${GREEN}  Verified branch: $branch${NC}"
        fi
        cd ..
    else
        echo -e "${GREEN}Cloning $repo...${NC}"
        git clone -b "$branch" "https://github.com/$GITHUB_USERNAME/$repo.git"
    fi
done

echo ""
echo -e "${GREEN}Repository setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. (Recommended) Use Pixi:"
echo "     cd volttron-installer"
echo "     pixi run run"
echo ""
echo "  2. (Manual) Setup virtualenv manually as described in README.md"
