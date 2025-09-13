"""Test cases for the Red Hat logo tool."""

import base64
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from template_mcp_server.src.tools.redhat_logo import read_redhat_logo_content


class TestRedHatLogoTool:
    """Test cases for the read_redhat_logo_content function."""

    @pytest.mark.asyncio
    async def test_read_logo_success(self):
        """Test successful reading of the Red Hat logo."""
        # Mock PNG data
        mock_png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        )
        expected_base64 = base64.b64encode(mock_png_data).decode("utf-8")

        with patch("builtins.open", mock_open(read_data=mock_png_data)):
            result = await read_redhat_logo_content()

        assert result["name"] == "Red Hat Logo"
        assert result["description"] == "Red Hat logo as base64 encoded PNG"
        assert result["mimeType"] == "image/png"
        assert result["text"] == expected_base64

    @pytest.mark.asyncio
    async def test_read_logo_file_not_found(self):
        """Test behavior when logo file is not found."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            result = await read_redhat_logo_content()

        assert result["name"] == "Red Hat Logo Error"
        assert result["description"] == "Could not find Red Hat logo file"
        assert result["mimeType"] == "text/plain"
        assert "Error: Could not find logo file at" in result["text"]

    @pytest.mark.asyncio
    async def test_read_logo_permission_error(self):
        """Test behavior when there's a permission error."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = await read_redhat_logo_content()

        assert result["name"] == "Red Hat Logo Error"
        assert result["description"] == "Error reading Red Hat logo file"
        assert result["mimeType"] == "text/plain"
        assert "Error: Permission denied" in result["text"]

    @pytest.mark.asyncio
    async def test_read_logo_generic_error(self):
        """Test behavior when there's a generic error."""
        with patch("builtins.open", side_effect=IOError("I/O error")):
            result = await read_redhat_logo_content()

        assert result["name"] == "Red Hat Logo Error"
        assert result["description"] == "Error reading Red Hat logo file"
        assert result["mimeType"] == "text/plain"
        assert "Error: I/O error" in result["text"]

    @pytest.mark.asyncio
    async def test_read_logo_empty_file(self):
        """Test behavior when logo file is empty."""
        with patch("builtins.open", mock_open(read_data=b"")):
            result = await read_redhat_logo_content()

        assert result["name"] == "Red Hat Logo"
        assert result["description"] == "Red Hat logo as base64 encoded PNG"
        assert result["mimeType"] == "image/png"
        assert result["text"] == ""  # Empty base64

    @pytest.mark.asyncio
    async def test_read_logo_large_file(self):
        """Test behavior with a large file."""
        # Create a large mock file (1MB of data)
        large_data = b"x" * (1024 * 1024)
        expected_base64 = base64.b64encode(large_data).decode("utf-8")

        with patch("builtins.open", mock_open(read_data=large_data)):
            result = await read_redhat_logo_content()

        assert result["name"] == "Red Hat Logo"
        assert result["description"] == "Red Hat logo as base64 encoded PNG"
        assert result["mimeType"] == "image/png"
        assert result["text"] == expected_base64
        assert len(result["text"]) > 1000000  # Should be larger due to base64 encoding

    @pytest.mark.asyncio
    async def test_read_logo_binary_data(self):
        """Test with actual binary PNG-like data."""
        # Simulate actual PNG file header and some data
        png_header = b"\x89PNG\r\n\x1a\n"
        ihdr_chunk = b"\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6"
        mock_png = png_header + ihdr_chunk

        expected_base64 = base64.b64encode(mock_png).decode("utf-8")

        with patch("builtins.open", mock_open(read_data=mock_png)):
            result = await read_redhat_logo_content()

        assert result["name"] == "Red Hat Logo"
        assert result["mimeType"] == "image/png"
        assert result["text"] == expected_base64

    @pytest.mark.asyncio
    async def test_path_construction(self):
        """Test that the correct path is constructed."""
        mock_png_data = b"test_data"

        with patch("builtins.open", mock_open(read_data=mock_png_data)) as mock_file:
            await read_redhat_logo_content()

            # Verify that open was called (path construction worked)
            assert mock_file.called

    @pytest.mark.asyncio
    async def test_base64_encoding_correctness(self):
        """Test that base64 encoding is done correctly."""
        test_data = b"Hello, World!"
        expected_base64 = base64.b64encode(test_data).decode("utf-8")

        with patch("builtins.open", mock_open(read_data=test_data)):
            result = await read_redhat_logo_content()

        # Verify the base64 encoding is correct
        decoded_data = base64.b64decode(result["text"])
        assert decoded_data == test_data
        assert result["text"] == expected_base64

    @pytest.mark.asyncio
    async def test_unicode_decode_error(self):
        """Test behavior when base64 encoding fails."""
        with patch("builtins.open", mock_open(read_data=b"test")):
            with patch("base64.b64encode", side_effect=Exception("Encoding error")):
                result = await read_redhat_logo_content()

        assert result["name"] == "Red Hat Logo Error"
        assert result["description"] == "Error reading Red Hat logo file"
        assert result["mimeType"] == "text/plain"
        assert "Error: Encoding error" in result["text"]
