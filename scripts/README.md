# Template Transformation Scripts

This directory contains automation scripts to help developers create new MCP servers from this template.

## transform-template.sh

Automated script that transforms this `template-mcp-server` into your domain-specific MCP server by handling all the renaming and reference updates automatically.

### Usage

The script can be used in two ways:

#### Option 1: Download Script Only (Recommended)

```bash
# Download just the script to your workspace directory
curl -O https://raw.githubusercontent.com/redhat-data-and-ai/template-mcp-server/main/scripts/transform-template.sh

# Make it executable and run it
chmod +x transform-template.sh
./transform-template.sh <new-project-name>
```

#### Option 2: From Cloned Repository

⚠️ **Important**: Run the script FROM OUTSIDE the template directory:

```bash
# Clone the template first
git clone https://github.com/redhat-data-and-ai/template-mcp-server.git

# Run transformation script from your workspace directory (NOT inside the template)
./template-mcp-server/scripts/transform-template.sh <new-project-name>
```

### Examples

```bash
# Create a sales territory MCP server
./transform-template.sh "sales-territory-mcp-server"

# Create a data analysis MCP server
./transform-template.sh "data-analysis-mcp-server"

# Create a customer support MCP server
./transform-template.sh "customer-support-mcp-server"
```

### Rules

- **new-project-name**: Must be in kebab-case (lowercase with hyphens)
- **Python package name**: Will be auto-generated as snake_case
- **Class names**: Will be auto-generated as PascalCase

### What the Script Does

The transformation script automatically:

1. **Validates input** - Ensures proper naming conventions
2. **Creates directory structure** - Sets up the new project directories
3. **Renames files and directories** - Updates all template references
4. **Updates file contents** - Replaces template strings with your project name
5. **Updates configuration** - Modifies pyproject.toml, Containerfile, etc.
6. **Preserves functionality** - Maintains all existing features and tests
7. **Updates documentation** - Adjusts README and other docs for your project

### Before Running

#### For Option 1 (Download Script Only):

1. **Create or navigate to your workspace directory** where you want new projects created

2. **Download and run the script**:
   ```bash
   curl -O https://raw.githubusercontent.com/redhat-data-and-ai/template-mcp-server/main/scripts/transform-template.sh
   chmod +x transform-template.sh
   ./transform-template.sh "your-new-project-name"
   ```

#### For Option 2 (Clone First):

1. **Clone the template repository** (but don't change into it):
   ```bash
   git clone https://github.com/redhat-data-and-ai/template-mcp-server.git
   ```

2. **Run the transformation script from your workspace directory**:
   ```bash
   ./template-mcp-server/scripts/transform-template.sh "your-new-project-name"
   ```

⚠️ **Critical**: Never run the script from inside the template directory, as it's designed to clone and transform from outside.

### After Running

The script will create a new directory with your project name containing:

- ✅ **Renamed Python package** with your domain-specific name
- ✅ **Updated configuration files** (pyproject.toml, Containerfile, etc.)
- ✅ **Modified documentation** (README.md, etc.)
- ✅ **Working tests** adapted to your project
- ✅ **Container and deployment configs** ready for your use case
- ✅ **Development tools** (pre-commit, linting, etc.) configured

### Next Steps

After transformation:

1. **Navigate to your new project**:

   ```bash
   cd your-new-project-name
   ```

2. **⚠️ CRITICAL: Install dependencies** (required for imports to work):

   ```bash
   make install
   ```

3. **Verify everything works**:

   ```bash
   make test
   ```

4. **Start your customized server**:

   ```bash
   make local
   ```

5. **Start developing** your domain-specific tools and functionality!

### Troubleshooting

- **ModuleNotFoundError** (e.g., `No module named 'your_project_name'`): You forgot to install dependencies after transformation. Run `make install` in your new project directory.
- **Permission denied**: Ensure the script is executable with `chmod +x transform-template.sh`
- **Invalid name**: Use kebab-case (lowercase with hyphens only)
- **Directory exists**: The script will not overwrite existing directories
- **Script fails to clone**: Ensure you have internet access and git is installed
- **Wrong directory structure**: The script should be run from your workspace directory, not inside the template
- **Git issues**: Ensure you're in a clean git state before running

For more details about MCP server development, see the main [README.md](../README.md).
