"""Tests for Zotero client module"""

import os
from unittest.mock import patch

import pytest

from zotero_mcp.client import get_zotero_client


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    with patch.dict(
        os.environ,
        {
            "ZOTERO_LIBRARY_ID": "1234567",
            "ZOTERO_LIBRARY_TYPE": "user",
            "ZOTERO_API_KEY": "abcdef123456",
            "ZOTERO_LOCAL": "",
        },
        clear=True,
    ):
        yield


@pytest.fixture
def mock_env_vars_local():
    """Mock environment variables for local mode"""
    with patch.dict(
        os.environ,
        {
            "ZOTERO_LIBRARY_ID": "",
            "ZOTERO_LIBRARY_TYPE": "user",
            "ZOTERO_API_KEY": "",
            "ZOTERO_LOCAL": "true",
        },
        clear=True,
    ):
        yield


def test_get_zotero_client_with_api_key(mock_env_vars):
    """Test client initialization with API key"""
    with patch("zotero_mcp.client.zotero.Zotero") as mock_zotero:
        get_zotero_client()
        mock_zotero.assert_called_once_with(
            library_id="1234567",
            library_type="user",
            api_key="abcdef123456",
            local=False,
        )


def test_get_zotero_client_missing_api_key():
    """Test client initialization with missing API key"""
    with patch.dict(
        os.environ,
        {
            "ZOTERO_LIBRARY_ID": "1234567",
            "ZOTERO_LIBRARY_TYPE": "user",
            "ZOTERO_API_KEY": "",
            "ZOTERO_LOCAL": "",
        },
        clear=True,
    ):
        with pytest.raises(ValueError) as excinfo:
            get_zotero_client()
        assert "Missing required environment variables" in str(excinfo.value)


def test_get_zotero_client_local_mode(mock_env_vars_local):
    """Test client initialization in local mode"""
    with patch("zotero_mcp.client.zotero.Zotero") as mock_zotero:
        get_zotero_client()
        mock_zotero.assert_called_once_with(
            library_id="0",
            library_type="user",
            api_key=None,
            local=True,
        )


def test_get_zotero_client_local_mode_with_library_id():
    """Test client initialization in local mode with custom library ID"""
    with (
        patch.dict(
            os.environ,
            {
                "ZOTERO_LIBRARY_ID": "custom_id",
                "ZOTERO_LIBRARY_TYPE": "user",
                "ZOTERO_API_KEY": "",
                "ZOTERO_LOCAL": "true",
            },
            clear=True,
        ),
        patch("zotero_mcp.client.zotero.Zotero") as mock_zotero,
    ):
        get_zotero_client()
        mock_zotero.assert_called_once_with(
            library_id="custom_id",
            library_type="user",
            api_key=None,
            local=True,
        )
