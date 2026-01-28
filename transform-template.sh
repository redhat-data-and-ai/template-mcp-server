#!/bin/bash
# transform-template.sh
# Dataverse MCP Server Template Transformation Script
#
# This script transforms the template-mcp-server into a domain-specific MCP server
# by handling all the renaming and reference updates automatically.
#
# Usage: ./transform-template.sh <new-project-name>
# Example: ./transform-template.sh "sales-territory-mcp-server"

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Validate arguments
if [ $# -ne 1 ]; then
    print_error "Usage: $0 <new-project-name>"
    echo ""
    echo "Examples:"
    echo "  $0 'sales-territory-mcp-server'"
    echo "  $0 'data-analysis-mcp-server'"
    echo ""
    echo "Rules:"
    echo "  - new-project-name: kebab-case (lowercase with hyphens)"
    echo "  - Python package name will be auto-generated as snake_case"
    exit 1
fi

NEW_PROJECT_NAME="$1"
# Auto-generate snake_case version from kebab-case
NEW_SRC_NAME=$(echo "$NEW_PROJECT_NAME" | sed 's/-/_/g')

# Validate naming conventions
if [[ ! "$NEW_PROJECT_NAME" =~ ^[a-z0-9-]+$ ]]; then
    print_error "Project name must be kebab-case: lowercase letters, numbers, and hyphens only"
    exit 1
fi

# Validate auto-generated snake_case name
if [[ ! "$NEW_SRC_NAME" =~ ^[a-z0-9_]+$ ]]; then
    print_error "Auto-generated Python package name '$NEW_SRC_NAME' is invalid"
    print_warning "This usually means the project name contains invalid characters"
    exit 1
fi

# Check if target directory already exists
if [ -d "$NEW_PROJECT_NAME" ]; then
    print_error "Target directory '$NEW_PROJECT_NAME' already exists"
    print_warning "Please remove it or choose a different name"
    exit 1
fi

echo ""
echo "🚀 Dataverse MCP Server Template Transformation"
echo "=============================================="
echo ""
echo "Creating new MCP server:"
echo "  📁 Project Name: $NEW_PROJECT_NAME"
echo "  🐍 Python Package: $NEW_SRC_NAME (auto-generated)"
echo ""

# Step 1: Clone template directly to new project name
print_step "Cloning template to new project directory..."
git clone https://github.com/redhat-data-and-ai/template-mcp-server.git "$NEW_PROJECT_NAME"
if [ $? -ne 0 ]; then
    print_error "Failed to clone template repository"
    print_warning "Make sure you have access to: https://github.com/redhat-data-and-ai/template-mcp-server.git"
    exit 1
fi
cd "$NEW_PROJECT_NAME"
print_success "Template cloned as $NEW_PROJECT_NAME"

# Step 2: Rename the Python package directory
print_step "Renaming Python package directory..."
if [ -d "template_mcp_server" ]; then
    mv template_mcp_server "$NEW_SRC_NAME"
    print_success "Package renamed to $NEW_SRC_NAME"
else
    print_warning "template_mcp_server directory not found, skipping..."
fi

# Step 3: Update Python imports and references
print_step "Updating Python imports and references..."
find . -name "*.py" -type f -exec sed -i.bak "s/template_mcp_server/$NEW_SRC_NAME/g" {} \; 2>/dev/null || {
    # Fallback for systems without -i flag support
    find . -name "*.py" -type f | while read -r file; do
        sed "s/template_mcp_server/$NEW_SRC_NAME/g" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    done
}
print_success "Updated Python references"

# Step 4: Update configuration files (pyproject.toml, etc.)
print_step "Updating configuration files..."

# Update pyproject.toml
if [ -f "pyproject.toml" ]; then
    sed -i.bak "s/template_mcp_server/$NEW_SRC_NAME/g" pyproject.toml 2>/dev/null || {
        sed "s/template_mcp_server/$NEW_SRC_NAME/g" pyproject.toml > pyproject.toml.tmp && mv pyproject.toml.tmp pyproject.toml
    }
    sed -i.bak "s/template-mcp-server/$NEW_PROJECT_NAME/g" pyproject.toml 2>/dev/null || {
        sed "s/template-mcp-server/$NEW_PROJECT_NAME/g" pyproject.toml > pyproject.toml.tmp && mv pyproject.toml.tmp pyproject.toml
    }
fi

# Update other TOML files
find . -name "*.toml" -type f -exec sed -i.bak "s/template_mcp_server/$NEW_SRC_NAME/g" {} \; 2>/dev/null || {
    find . -name "*.toml" -type f | while read -r file; do
        sed "s/template_mcp_server/$NEW_SRC_NAME/g" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
        sed "s/template-mcp-server/$NEW_PROJECT_NAME/g" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    done
}
print_success "Updated configuration files"

# Step 5: Update YAML/container configurations
print_step "Updating YAML and container configurations..."

# Update YAML files
find . -name "*.yaml" -o -name "*.yml" -type f | while read -r file; do
    sed -i.bak "s/template-mcp-server/$NEW_PROJECT_NAME/g" "$file" 2>/dev/null || {
        sed "s/template-mcp-server/$NEW_PROJECT_NAME/g" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    }
done

# Update Containerfiles
find . -name "Containerfile*" -type f | while read -r file; do
    # Update kebab-case project name
    sed -i.bak "s/template-mcp-server/$NEW_PROJECT_NAME/g" "$file" 2>/dev/null || {
        sed "s/template-mcp-server/$NEW_PROJECT_NAME/g" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    }
    # Update snake_case package name
    sed -i.bak "s/template_mcp_server/$NEW_SRC_NAME/g" "$file" 2>/dev/null || {
        sed "s/template_mcp_server/$NEW_SRC_NAME/g" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    }
done

print_success "Updated container configurations"

# Step 6: Update documentation files
print_step "Updating documentation files..."

find . -name "*.md" -type f | while read -r file; do
    # Update project references
    sed -i.bak "s/template-mcp-server/$NEW_PROJECT_NAME/g" "$file" 2>/dev/null || {
        sed "s/template-mcp-server/$NEW_PROJECT_NAME/g" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    }
    # Update Python package references
    sed -i.bak "s/template_mcp_server/$NEW_SRC_NAME/g" "$file" 2>/dev/null || {
        sed "s/template_mcp_server/$NEW_SRC_NAME/g" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    }
done

# Update other text files
find . -name "*.txt" -type f | while read -r file; do
    sed -i.bak "s/template-mcp-server/$NEW_PROJECT_NAME/g" "$file" 2>/dev/null || {
        sed "s/template-mcp-server/$NEW_PROJECT_NAME/g" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    }
done

print_success "Updated documentation"

# Step 7: Clean up backup files
print_step "Cleaning up backup files..."
find . -name "*.bak" -type f -delete 2>/dev/null || true
print_success "Cleaned up temporary files"

# Step 8: Verification
print_step "Verifying transformation..."

TEMPLATE_REFS=$(grep -r "template_mcp_server" . --exclude-dir=.git 2>/dev/null | wc -l | awk '{print $1}' || echo "0")
PROJECT_REFS=$(grep -r "template-mcp-server" . --exclude-dir=.git 2>/dev/null | wc -l | awk '{print $1}' || echo "0")

if [ "$TEMPLATE_REFS" -eq 0 ] && [ "$PROJECT_REFS" -eq 0 ]; then
    print_success "All template references updated successfully!"
else
    print_warning "Some template references may remain:"
    if [ "$TEMPLATE_REFS" -gt 0 ]; then
        echo "  - Python package references: $TEMPLATE_REFS"
    fi
    if [ "$PROJECT_REFS" -gt 0 ]; then
        echo "  - Project name references: $PROJECT_REFS"
    fi
    echo ""
    echo "You may need to manually update these remaining references."
fi

# Step 9: Run regression tests to verify transformation
print_step "Running regression tests to verify transformation..."

# Check if we have a virtual environment or dependencies
if [ ! -f "pyproject.toml" ]; then
    print_warning "No pyproject.toml found, skipping tests"
elif command -v uv >/dev/null 2>&1; then
    # Try with uv first
    if uv run pytest tests/ -v 2>/dev/null; then
        print_success "✅ All tests passed! Transformation verified successfully"
    else
        print_warning "⚠️  Some tests failed, but this might be expected for domain-specific logic"
        echo "  You can run tests manually with: uv run pytest tests/"
    fi
elif command -v pytest >/dev/null 2>&1; then
    # Fallback to system pytest
    if pytest tests/ -v 2>/dev/null; then
        print_success "✅ All tests passed! Transformation verified successfully"
    else
        print_warning "⚠️  Some tests failed, but this might be expected for domain-specific logic"
        echo "  You can run tests manually with: pytest tests/"
    fi
else
    print_warning "Neither 'uv' nor 'pytest' found, skipping test verification"
    echo "  Install dependencies first: uv pip install -e \".[dev]\""
    echo "  Then run tests with: uv run pytest tests/"
fi

# Step 10: Final steps guidance
echo ""
echo "🎉 Transformation Complete!"
echo "=========================="
echo ""
echo "Your new MCP server is ready in: $(pwd)"
echo ""
print_success "Next steps:"
echo "  1. Set up development environment:"
echo "     uv venv --python 3.12 && source .venv/bin/activate"
echo ""
echo "  2. Install dependencies:"
echo "     uv pip install -e \".[dev]\""
echo ""
echo "  3. Install internal certificates:"
echo "     wget https://certs.path.example.com/ca-cert.pem \\"
echo "       && cat ca-cert.pem >> \`python -m certifi\`"
echo ""
echo "  4. Start customizing your tools in:"
echo "     📁 $NEW_SRC_NAME/src/tools/"
echo ""
echo "  5. Test your server:"
echo "     python -m $NEW_SRC_NAME.src.main"
echo ""
echo "  6. Run tests anytime:"
echo "     uv run pytest tests/          # Run all tests"
echo "     uv run pytest tests/ -v      # Verbose output"
echo "     uv run pytest tests/ -k test_basic  # Run specific tests"
echo ""
print_warning "Remember to:"
echo "  • Update the README.md with your domain-specific information"
echo "  • Customize the tools in src/tools/ for your use case"
echo "  • Add your own tests to tests/ directory as you develop"
echo "  • Run 'uv run pytest tests/' to verify your changes"
echo "  • Update the OpenShift configs in openshift/ directory"
echo "  • Set up your GitLab repository and push your changes"
echo ""
echo "Happy MCP server development! 🚀"
