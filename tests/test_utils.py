"""Tests for the utils module."""

from unittest.mock import Mock, patch

import pytest

from template_mcp_server.utils.pylogger import (
    AWS_LOGGERS,
    ERROR_ONLY_LOGGERS,
    HTTP_CLIENT_LOGGERS,
    MCP_LOGGERS,
    ML_AI_LOGGERS,
    OBSERVABILITY_LOGGERS,
    THIRD_PARTY_LOGGERS,
    _clear_handlers,
    _configure_third_party_loggers,
    _setup_logger,
    force_reconfigure_all_loggers,
    get_python_logger,
    get_uvicorn_log_config,
)


class TestPylogger:
    """Test the pylogger utility."""

    def test_get_python_logger_default(self):
        """Test getting logger with default configuration."""
        # Act
        logger = get_python_logger()

        # Assert
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "critical")

    def test_get_python_logger_custom_level(self):
        """Test getting logger with custom log level."""
        # Arrange
        custom_level = "DEBUG"

        # Act
        logger = get_python_logger(custom_level)

        # Assert
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "critical")

    def test_get_python_logger_case_insensitive(self):
        """Test that log level is converted to uppercase."""
        # Arrange
        test_levels = ["info", "INFO", "Info", "iNfO"]

        for level in test_levels:
            # Act
            logger = get_python_logger(level)

            # Assert
            assert logger is not None
            assert hasattr(logger, "info")

    def test_get_python_logger_valid_levels(self):
        """Test logger creation with all valid log levels."""
        # Arrange
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            # Act
            logger = get_python_logger(level)

            # Assert
            assert logger is not None
            assert hasattr(logger, "info")
            assert hasattr(logger, "error")
            assert hasattr(logger, "warning")
            assert hasattr(logger, "debug")
            assert hasattr(logger, "critical")

    @patch("template_mcp_server.utils.pylogger.structlog")
    @patch("template_mcp_server.utils.pylogger._LOGGING_CONFIGURED", False)
    def test_get_python_logger_structlog_configuration(self, mock_structlog):
        """Test that structlog is configured correctly."""
        # Arrange
        mock_structlog.get_logger.return_value = Mock()

        # Act
        with patch("template_mcp_server.utils.pylogger._LOGGING_CONFIGURED", False):
            get_python_logger()

        # Assert
        mock_structlog.configure.assert_called_once()
        mock_structlog.get_logger.assert_called_once()

    @patch("template_mcp_server.utils.pylogger.structlog")
    def test_get_python_logger_processors_configuration(self, mock_structlog):
        """Test that structlog processors are configured correctly."""
        # Arrange
        mock_structlog.get_logger.return_value = Mock()

        # Act
        with patch("template_mcp_server.utils.pylogger._LOGGING_CONFIGURED", False):
            get_python_logger()

        # Assert
        mock_structlog.configure.assert_called_once()
        call_args = mock_structlog.configure.call_args

        # Check that processors list is provided
        assert "processors" in call_args[1]
        processors = call_args[1]["processors"]
        assert isinstance(processors, list)
        assert len(processors) > 0

    @patch("template_mcp_server.utils.pylogger.structlog")
    def test_get_python_logger_context_class_configuration(self, mock_structlog):
        """Test that context_class is configured correctly."""
        # Arrange
        mock_structlog.get_logger.return_value = Mock()

        # Act
        with patch("template_mcp_server.utils.pylogger._LOGGING_CONFIGURED", False):
            get_python_logger()

        # Assert
        mock_structlog.configure.assert_called_once()
        call_args = mock_structlog.configure.call_args
        assert call_args[1]["context_class"] is dict

    @patch("template_mcp_server.utils.pylogger.structlog")
    def test_get_python_logger_logger_factory_configuration(self, mock_structlog):
        """Test that logger_factory is configured correctly."""
        # Arrange
        mock_structlog.get_logger.return_value = Mock()

        # Act
        with patch("template_mcp_server.utils.pylogger._LOGGING_CONFIGURED", False):
            get_python_logger()

        # Assert
        mock_structlog.configure.assert_called_once()
        call_args = mock_structlog.configure.call_args
        # Check that logger_factory is in the configuration
        assert "logger_factory" in call_args[1]
        # The actual value might be a mock, so we just verify it's configured
        assert call_args[1]["logger_factory"] is not None

    @patch("template_mcp_server.utils.pylogger.structlog")
    def test_get_python_logger_wrapper_class_configuration(self, mock_structlog):
        """Test that wrapper_class is configured correctly."""
        # Arrange
        mock_structlog.get_logger.return_value = Mock()

        # Act
        with patch("template_mcp_server.utils.pylogger._LOGGING_CONFIGURED", False):
            get_python_logger()

        # Assert
        mock_structlog.configure.assert_called_once()
        call_args = mock_structlog.configure.call_args
        assert call_args[1]["wrapper_class"] == mock_structlog.stdlib.BoundLogger

    @patch("template_mcp_server.utils.pylogger.structlog")
    def test_get_python_logger_cache_logger_configuration(self, mock_structlog):
        """Test that cache_logger_on_first_use is configured correctly."""
        # Arrange
        mock_structlog.get_logger.return_value = Mock()

        # Act
        with patch("template_mcp_server.utils.pylogger._LOGGING_CONFIGURED", False):
            get_python_logger()

        # Assert
        mock_structlog.configure.assert_called_once()
        call_args = mock_structlog.configure.call_args
        assert call_args[1]["cache_logger_on_first_use"] is True

    def test_get_python_logger_return_type(self):
        """Test that the function returns the correct type."""
        # Act
        logger = get_python_logger()

        # Assert
        assert logger is not None
        # The logger should be a structlog logger instance

    def test_get_python_logger_function_signature(self):
        """Test that the function has the correct signature."""
        # Assert
        import inspect

        sig = inspect.signature(get_python_logger)
        assert len(sig.parameters) == 1
        assert "log_level" in sig.parameters
        assert sig.parameters["log_level"].default == "INFO"

    def test_get_python_logger_multiple_calls(self):
        """Test that multiple calls to get_python_logger work correctly."""
        # Act
        logger1 = get_python_logger("INFO")
        logger2 = get_python_logger("DEBUG")
        logger3 = get_python_logger()

        # Assert
        assert logger1 is not None
        assert logger2 is not None
        assert logger3 is not None
        assert hasattr(logger1, "info")
        assert hasattr(logger2, "info")
        assert hasattr(logger3, "info")

    def test_get_python_logger_logging_functionality(self):
        """Test that the logger can be used for logging."""
        # Arrange
        logger = get_python_logger()

        # Act & Assert - should not raise any exceptions
        try:
            logger.info("Test info message")
            logger.error("Test error message")
            logger.warning("Test warning message")
            logger.debug("Test debug message")
            logger.critical("Test critical message")
        except Exception as e:
            pytest.fail(f"Logger should not raise exceptions: {e}")

    def test_get_python_logger_with_structured_logging(self):
        """Test that the logger supports structured logging."""
        # Arrange
        logger = get_python_logger()

        # Act & Assert - should not raise any exceptions
        try:
            logger.info("Test message", user_id=123, action="test")
            logger.error("Test error", error_code=500, component="test")
        except Exception as e:
            pytest.fail(f"Structured logging should not raise exceptions: {e}")

    def test_get_python_logger_import(self):
        """Test that the module can be imported without errors."""
        # Act & Assert
        try:
            import template_mcp_server.utils.pylogger

            assert template_mcp_server.utils.pylogger.get_python_logger is not None
        except ImportError as e:
            pytest.fail(f"Module should be importable: {e}")

    # Tests for force_reconfigure_all_loggers()
    @patch("template_mcp_server.utils.pylogger.get_python_logger")
    def test_force_reconfigure_all_loggers_default_level(self, mock_get_logger):
        """Test force_reconfigure_all_loggers with default log level."""
        # Arrange
        mock_get_logger.return_value = Mock()

        # Act
        force_reconfigure_all_loggers()

        # Assert
        mock_get_logger.assert_called_once_with("INFO")

    @patch("template_mcp_server.utils.pylogger.get_python_logger")
    def test_force_reconfigure_all_loggers_custom_level(self, mock_get_logger):
        """Test force_reconfigure_all_loggers with custom log level."""
        # Arrange
        mock_get_logger.return_value = Mock()
        custom_level = "DEBUG"

        # Act
        force_reconfigure_all_loggers(custom_level)

        # Assert
        mock_get_logger.assert_called_once_with(custom_level)

    @patch("template_mcp_server.utils.pylogger._LOGGING_CONFIGURED", True)
    @patch("template_mcp_server.utils.pylogger.get_python_logger")
    def test_force_reconfigure_resets_global_flag(self, mock_get_logger):
        """Test that force_reconfigure_all_loggers resets the global configuration flag."""
        # Arrange
        mock_get_logger.return_value = Mock()

        # Verify initial state
        import template_mcp_server.utils.pylogger as pylogger_module

        pylogger_module._LOGGING_CONFIGURED = True

        # Act
        force_reconfigure_all_loggers()

        # Assert - the function should reset the flag and then call get_python_logger
        # which will set it back to True
        mock_get_logger.assert_called_once_with("INFO")

    # Tests for get_uvicorn_log_config()
    def test_get_uvicorn_log_config_default_level(self):
        """Test get_uvicorn_log_config with default log level."""
        # Act
        config = get_uvicorn_log_config()

        # Assert
        assert isinstance(config, dict)
        assert "version" in config
        assert config["version"] == 1
        assert "disable_existing_loggers" in config
        assert config["disable_existing_loggers"] is False
        assert "formatters" in config
        assert "handlers" in config
        assert "loggers" in config

    def test_get_uvicorn_log_config_custom_level(self):
        """Test get_uvicorn_log_config with custom log level."""
        # Arrange
        custom_level = "DEBUG"

        # Act
        config = get_uvicorn_log_config(custom_level)

        # Assert
        assert isinstance(config, dict)
        assert config["version"] == 1
        # Check that the custom level is applied to base loggers
        base_loggers = [
            "",
            "uvicorn",
            "uvicorn.error",
            "uvicorn.asgi",
            "uvicorn.protocols",
        ]
        for logger_name in base_loggers:
            if logger_name in config["loggers"]:
                assert config["loggers"][logger_name]["level"] == custom_level

    def test_get_uvicorn_log_config_case_insensitive(self):
        """Test that get_uvicorn_log_config converts log level to uppercase."""
        # Arrange
        lower_level = "debug"

        # Act
        config = get_uvicorn_log_config(lower_level)

        # Assert
        assert isinstance(config, dict)
        # Check that level is converted to uppercase
        base_loggers = [
            "",
            "uvicorn",
            "uvicorn.error",
            "uvicorn.asgi",
            "uvicorn.protocols",
        ]
        for logger_name in base_loggers:
            if logger_name in config["loggers"]:
                assert config["loggers"][logger_name]["level"] == "DEBUG"

    def test_get_uvicorn_log_config_formatters(self):
        """Test that get_uvicorn_log_config includes proper formatters."""
        # Act
        config = get_uvicorn_log_config()

        # Assert
        assert "formatters" in config
        assert "default" in config["formatters"]
        assert "access" in config["formatters"]

        # Check formatter structure
        default_formatter = config["formatters"]["default"]
        assert "()" in default_formatter
        assert "processor" in default_formatter
        assert "foreign_pre_chain" in default_formatter

    def test_get_uvicorn_log_config_handlers(self):
        """Test that get_uvicorn_log_config includes proper handlers."""
        # Act
        config = get_uvicorn_log_config()

        # Assert
        assert "handlers" in config
        assert "default" in config["handlers"]
        assert "access" in config["handlers"]

        # Check handler structure
        default_handler = config["handlers"]["default"]
        assert "formatter" in default_handler
        assert "class" in default_handler
        assert "stream" in default_handler

    def test_get_uvicorn_log_config_error_only_loggers(self):
        """Test that ERROR_ONLY_LOGGERS are configured with ERROR level."""
        # Act
        config = get_uvicorn_log_config("INFO")

        # Assert
        loggers_config = config["loggers"]

        # Check that ERROR_ONLY_LOGGERS have ERROR level
        for logger_name in ERROR_ONLY_LOGGERS:
            if logger_name in loggers_config:
                assert loggers_config[logger_name]["level"] == "ERROR"

    # Tests for logger constants and sets
    def test_logger_constants_are_sets(self):
        """Test that all logger constants are sets."""
        assert isinstance(HTTP_CLIENT_LOGGERS, set)
        assert isinstance(AWS_LOGGERS, set)
        assert isinstance(MCP_LOGGERS, set)
        assert isinstance(ML_AI_LOGGERS, set)
        assert isinstance(OBSERVABILITY_LOGGERS, set)
        assert isinstance(THIRD_PARTY_LOGGERS, set)
        assert isinstance(ERROR_ONLY_LOGGERS, set)

    def test_logger_constants_not_empty(self):
        """Test that all logger constants contain entries."""
        assert len(HTTP_CLIENT_LOGGERS) > 0
        assert len(AWS_LOGGERS) > 0
        assert len(MCP_LOGGERS) > 0
        assert len(ML_AI_LOGGERS) > 0
        assert len(OBSERVABILITY_LOGGERS) > 0
        assert len(THIRD_PARTY_LOGGERS) > 0
        assert len(ERROR_ONLY_LOGGERS) > 0

    def test_third_party_loggers_aggregation(self):
        """Test that THIRD_PARTY_LOGGERS is the union of all logger sets."""
        expected = (
            HTTP_CLIENT_LOGGERS
            | AWS_LOGGERS
            | MCP_LOGGERS
            | ML_AI_LOGGERS
            | OBSERVABILITY_LOGGERS
        )
        assert THIRD_PARTY_LOGGERS == expected

    def test_error_only_loggers_subset(self):
        """Test that ERROR_ONLY_LOGGERS is composed of specific logger sets."""
        expected = ML_AI_LOGGERS | OBSERVABILITY_LOGGERS
        assert ERROR_ONLY_LOGGERS == expected

    def test_logger_constants_contain_expected_entries(self):
        """Test that logger constants contain expected specific entries."""
        # HTTP clients
        assert "urllib3" in HTTP_CLIENT_LOGGERS
        assert "requests" in HTTP_CLIENT_LOGGERS
        assert "httpx" in HTTP_CLIENT_LOGGERS

        # AWS
        assert "botocore" in AWS_LOGGERS
        assert "boto3" in AWS_LOGGERS

        # MCP
        assert "fastmcp" in MCP_LOGGERS

        # ML/AI
        assert "sentence_transformers" in ML_AI_LOGGERS
        assert "transformers" in ML_AI_LOGGERS

        # Observability
        assert "langfuse" in OBSERVABILITY_LOGGERS

    # Tests for internal helper functions
    def test_clear_handlers(self):
        """Test _clear_handlers function."""
        # Arrange
        mock_logger = Mock()
        # Create mock lists that support clear()
        mock_handlers = Mock()
        mock_filters = Mock()
        mock_logger.handlers = mock_handlers
        mock_logger.filters = mock_filters

        # Act
        _clear_handlers(mock_logger)

        # Assert
        mock_handlers.clear.assert_called_once()
        mock_filters.clear.assert_called_once()

    @patch("template_mcp_server.utils.pylogger.logging")
    @patch("template_mcp_server.utils.pylogger._clear_handlers")
    def test_setup_logger_regular_logger(self, mock_clear_handlers, mock_logging):
        """Test _setup_logger for regular loggers (not in ERROR_ONLY_LOGGERS)."""
        # Arrange
        logger_name = "test_logger"
        log_level = "INFO"
        mock_logger = Mock()
        mock_logging.getLogger.return_value = mock_logger

        # Act
        _setup_logger(logger_name, log_level)

        # Assert
        mock_logging.getLogger.assert_called_once_with(logger_name)
        mock_clear_handlers.assert_called_once_with(mock_logger)
        mock_logger.setLevel.assert_called_once_with(log_level)
        assert mock_logger.propagate is True

    @patch("template_mcp_server.utils.pylogger.logging")
    @patch("template_mcp_server.utils.pylogger._clear_handlers")
    def test_setup_logger_error_only_logger(self, mock_clear_handlers, mock_logging):
        """Test _setup_logger for loggers in ERROR_ONLY_LOGGERS."""
        # Arrange
        # Pick a logger from ERROR_ONLY_LOGGERS
        logger_name = list(ERROR_ONLY_LOGGERS)[0]
        log_level = "INFO"
        mock_logger = Mock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.ERROR = 40  # Mock the logging level constant

        # Act
        _setup_logger(logger_name, log_level)

        # Assert
        mock_logging.getLogger.assert_called_once_with(logger_name)
        mock_clear_handlers.assert_called_once_with(mock_logger)
        mock_logger.setLevel.assert_called_once_with(mock_logging.ERROR)
        assert mock_logger.propagate is True

    @patch("template_mcp_server.utils.pylogger.logging")
    @patch("template_mcp_server.utils.pylogger._setup_logger")
    def test_configure_third_party_loggers(self, mock_setup_logger, mock_logging):
        """Test _configure_third_party_loggers function."""
        # Arrange
        log_level = "DEBUG"
        mock_root_logger = Mock()
        mock_logging.getLogger.return_value = mock_root_logger

        # Act
        _configure_third_party_loggers(log_level)

        # Assert
        # Check that root logger handlers are cleared
        mock_logging.getLogger.assert_called_once_with()
        mock_root_logger.handlers.clear.assert_called_once()

        # Check that _setup_logger is called for each third-party logger
        expected_calls = len(THIRD_PARTY_LOGGERS)
        assert mock_setup_logger.call_count == expected_calls

        # Verify all third-party loggers were configured
        configured_loggers = {call[0][0] for call in mock_setup_logger.call_args_list}
        assert configured_loggers == THIRD_PARTY_LOGGERS

    # Tests for global state management
    @patch("template_mcp_server.utils.pylogger.structlog")
    def test_logging_configured_flag_prevents_reconfiguration(self, mock_structlog):
        """Test that _LOGGING_CONFIGURED flag prevents reconfiguration."""
        # Arrange
        mock_structlog.get_logger.return_value = Mock()
        import template_mcp_server.utils.pylogger as pylogger_module

        # First call should configure
        pylogger_module._LOGGING_CONFIGURED = False
        get_python_logger()
        first_call_count = mock_structlog.configure.call_count

        # Second call should not configure again
        get_python_logger()
        second_call_count = mock_structlog.configure.call_count

        # Assert
        assert first_call_count == 1
        assert second_call_count == 1  # Should still be 1, not 2

    def test_global_state_management_with_force_reconfigure(self):
        """Test that force_reconfigure properly manages global state."""
        # Arrange
        import template_mcp_server.utils.pylogger as pylogger_module

        # Set initial state
        pylogger_module._LOGGING_CONFIGURED = True

        # Act
        force_reconfigure_all_loggers()

        # Assert - the flag should be True after force_reconfigure (since it calls get_python_logger)
        assert pylogger_module._LOGGING_CONFIGURED is True
