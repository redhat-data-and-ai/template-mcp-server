# Assets Directory

Static files accessed by MCP tools for data, images, templates, and other resources.

## 📁 **What Goes Here**

- 🖼️ **Images/Logos**: `company_logo.png`, `charts/sales_chart.jpg`
- 📄 **Templates**: `report_template.html`, `email_template.txt`
- 📊 **Data Files**: `reference_data.json`, `lookup_tables.csv`
- 📋 **Schemas**: `api_schema.json`, `validation_rules.yaml`
- 🔧 **Configs**: `model_config.json`, `processing_rules.xml`

## 🎯 **Usage in Tools**

### **Accessing Assets from Tools**

```python
# your_domain_mcp_server/src/tools/your_asset_tool.py
from pathlib import Path

def get_your_asset() -> Dict[str, Any]:
    """Tool to access static assets."""
    try:
        # Path construction from tools/ to assets/
        current_dir = Path(__file__).parent.parent  # Go up to src/
        assets_dir = current_dir / "assets"
        asset_path = assets_dir / "your_file.png"

        if not asset_path.exists():
            return {
                "status": "error",
                "error": "file_not_found",
                "message": f"Asset not found: {asset_path}"
            }

        # For binary files (images, etc.)
        with open(asset_path, "rb") as f:
            data = f.read()
            # Return as base64 for images
            import base64
            encoded_data = base64.b64encode(data).decode("utf-8")

        return {
            "status": "success",
            "name": "Your Asset",
            "data": encoded_data,
            "size_bytes": len(data),
            "message": "Asset retrieved successfully"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Asset retrieval failed"
        }
```

### **Text Files (Templates, JSON, etc.)**

```python
# For text files
with open(asset_path, "r", encoding="utf-8") as f:
    content = f.read()

return {
    "status": "success",
    "content": content,
    "encoding": "utf-8"
}
```

## 📋 **Current Assets**

- `redhat.png` - Red Hat logo (accessed by `redhat_logo_tool.py`)

## ✅ **Best Practices**

1. **Organize by type**: `images/`, `templates/`, `data/`, etc.
2. **Use descriptive names**: `quarterly_report_template.html` not `template1.html`
3. **Keep files small**: Large files should be external resources
4. **Version control friendly**: Avoid binary files when possible
5. **Document usage**: Note which tools access which assets
