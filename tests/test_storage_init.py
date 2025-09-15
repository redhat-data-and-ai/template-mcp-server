class TestStorageInit:
    """Test storage module __init__.py."""

    def test_storage_service_import(self):
        """Test that StorageService can be imported from storage module."""
        from template_mcp_server.src.storage.storage_service import StorageService

        # Should be able to import StorageService
        assert StorageService is not None
        assert hasattr(StorageService, "__init__")

    def test_storage_service_instantiation(self):
        """Test that StorageService can be instantiated."""
        from template_mcp_server.src.storage.storage_service import StorageService

        # Should be able to create instance with default parameters
        service = StorageService()
        assert service is not None
        assert service.host == "localhost"
        assert service.port == 5432

    def test_storage_service_instantiation_custom_params(self):
        """Test StorageService instantiation with custom parameters."""
        from template_mcp_server.src.storage.storage_service import StorageService

        service = StorageService(host="custom_host", port=5433, database="custom_db")
        assert service.host == "custom_host"
        assert service.port == 5433
        assert service.database == "custom_db"

    def test_module_docstring(self):
        """Test that module has proper docstring."""
        from template_mcp_server.src import storage

        assert storage.__doc__ is not None
        assert "PostgreSQL storage service" in storage.__doc__
