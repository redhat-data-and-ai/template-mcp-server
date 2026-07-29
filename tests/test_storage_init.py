class TestStorageInit:
    """Test storage module __init__.py."""

    def test_storage_service_import(self):
        """Test that StorageService can be imported from storage module."""
        from template_mcp_server.src.storage.storage_service import StorageService

        # Should be able to import StorageService
        assert StorageService is not None
        assert hasattr(StorageService, "__init__")

    def test_module_docstring(self):
        """Test that module has proper docstring."""
        from template_mcp_server.src import storage

        assert storage.__doc__ is not None
        assert "PostgreSQL storage service" in storage.__doc__
