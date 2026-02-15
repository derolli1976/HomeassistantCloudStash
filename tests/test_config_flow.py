#
# Tests for CloudStash – config_flow.py
#
# Unit tests for the config flow, endpoint normalisation, and connection
# probing logic.
#
# Author:       Oliver Stock (github.com/derolli1976)
# License:      MIT
#
# To run: pytest tests/test_config_flow.py
#

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from botocore.exceptions import (
    ClientError,
    ConnectionError as BotoConnectionError,
    ParamValidationError,
)

from custom_components.cloudstash.config_flow import (
    _normalise_endpoint,
    _probe_connection,
    SCHEMA_SETUP,
    CloudStashConfigFlow,
)
from custom_components.cloudstash.const import (
    DOMAIN,
    FALLBACK_REGION,
    OPT_BUCKET,
    OPT_ENDPOINT,
    OPT_KEY_ID,
    OPT_OBJECT_PREFIX,
    OPT_REGION,
    OPT_SECRET,
)


# ---------------------------------------------------------------------------
# _normalise_endpoint
# ---------------------------------------------------------------------------


class TestNormaliseEndpoint:
    """Tests for the endpoint URL normalisation helper."""

    def test_already_has_https(self):
        assert _normalise_endpoint("https://s3.example.com") == "https://s3.example.com"

    def test_already_has_http(self):
        assert _normalise_endpoint("http://minio.local:9000") == "http://minio.local:9000"

    def test_prepends_https_when_missing(self):
        assert _normalise_endpoint("s3.example.com") == "https://s3.example.com"

    def test_strips_whitespace(self):
        assert _normalise_endpoint("  https://s3.example.com  ") == "https://s3.example.com"

    def test_strips_trailing_slash(self):
        assert _normalise_endpoint("https://s3.example.com/") == "https://s3.example.com"

    def test_case_insensitive_scheme_check(self):
        assert _normalise_endpoint("HTTPS://s3.example.com") == "HTTPS://s3.example.com"

    def test_http_with_port(self):
        assert _normalise_endpoint("http://localhost:9000/") == "http://localhost:9000"

    def test_bare_hostname_with_port(self):
        assert _normalise_endpoint("minio.local:9000") == "https://minio.local:9000"


# ---------------------------------------------------------------------------
# _probe_connection
# ---------------------------------------------------------------------------


class TestProbeConnection:
    """Tests for the synchronous connection probe."""

    @patch("custom_components.cloudstash.config_flow.AioSession")
    def test_success(self, mock_session_cls):
        """A successful HeadBucket should not raise."""
        mock_client = AsyncMock()
        mock_client.head_bucket = AsyncMock(return_value={})

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.create_client.return_value = ctx
        mock_session_cls.return_value = mock_session

        # Should not raise
        _probe_connection(
            endpoint="https://s3.example.com",
            key_id="AKIA...",
            secret="secret",
            region="eu-central-1",
            bucket="test-bucket",
        )

    @patch("custom_components.cloudstash.config_flow.AioSession")
    def test_client_error_propagates(self, mock_session_cls):
        """A ClientError (e.g. 403) should propagate to the caller."""
        error_response = {"Error": {"Code": "403", "Message": "Forbidden"}}
        mock_client = AsyncMock()
        mock_client.head_bucket = AsyncMock(
            side_effect=ClientError(error_response, "HeadBucket")
        )

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.create_client.return_value = ctx
        mock_session_cls.return_value = mock_session

        with pytest.raises(ClientError):
            _probe_connection(
                endpoint="https://s3.example.com",
                key_id="BAD_KEY",
                secret="BAD_SECRET",
                region="us-east-1",
                bucket="test-bucket",
            )

    @patch("custom_components.cloudstash.config_flow.AioSession")
    def test_connection_error_propagates(self, mock_session_cls):
        """A BotoConnectionError should propagate to the caller."""
        mock_client = AsyncMock()
        mock_client.head_bucket = AsyncMock(
            side_effect=BotoConnectionError(error="unreachable")
        )

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.create_client.return_value = ctx
        mock_session_cls.return_value = mock_session

        with pytest.raises(BotoConnectionError):
            _probe_connection(
                endpoint="https://not-there.example.com",
                key_id="KEY",
                secret="SECRET",
                region="us-east-1",
                bucket="test-bucket",
            )


# ---------------------------------------------------------------------------
# CloudStashConfigFlow._try_connect
# ---------------------------------------------------------------------------


class TestTryConnect:
    """Tests for the shared _try_connect validation method."""

    @pytest.fixture
    def flow(self):
        """Create a CloudStashConfigFlow with a mocked hass."""
        f = CloudStashConfigFlow()
        f.hass = MagicMock()
        f.hass.async_add_executor_job = AsyncMock()
        return f

    async def test_success_returns_empty_errors(self, flow, sample_config):
        """Successful connection probe returns no errors."""
        flow.hass.async_add_executor_job.return_value = None
        errors = await flow._try_connect(sample_config)
        assert errors == {}

    async def test_client_error_returns_invalid_credentials(self, flow, sample_config):
        error_response = {"Error": {"Code": "403", "Message": "Forbidden"}}
        flow.hass.async_add_executor_job.side_effect = ClientError(
            error_response, "HeadBucket"
        )
        errors = await flow._try_connect(sample_config)
        assert errors == {"base": "invalid_credentials"}

    async def test_invalid_bucket_name(self, flow, sample_config):
        flow.hass.async_add_executor_job.side_effect = ParamValidationError(
            report="Invalid bucket name"
        )
        errors = await flow._try_connect(sample_config)
        assert errors == {OPT_BUCKET: "invalid_bucket_name"}

    async def test_value_error_returns_invalid_endpoint(self, flow, sample_config):
        flow.hass.async_add_executor_job.side_effect = ValueError("bad endpoint")
        errors = await flow._try_connect(sample_config)
        assert errors == {OPT_ENDPOINT: "invalid_endpoint_url"}

    async def test_connection_error_returns_cannot_connect(self, flow, sample_config):
        flow.hass.async_add_executor_job.side_effect = BotoConnectionError(
            error="unreachable"
        )
        errors = await flow._try_connect(sample_config)
        assert errors == {OPT_ENDPOINT: "cannot_connect"}


# ---------------------------------------------------------------------------
# Form schemas
# ---------------------------------------------------------------------------


class TestFormSchemas:
    """Verify that the voluptuous schemas are well-formed."""

    def test_setup_schema_has_required_keys(self):
        """SCHEMA_SETUP must contain all config keys."""
        schema_keys = {str(k) for k in SCHEMA_SETUP.schema}
        assert OPT_KEY_ID in schema_keys
        assert OPT_SECRET in schema_keys
        assert OPT_BUCKET in schema_keys
        assert OPT_ENDPOINT in schema_keys
        assert OPT_REGION in schema_keys
        assert OPT_OBJECT_PREFIX in schema_keys

    def test_setup_schema_defaults(self):
        """SCHEMA_SETUP should set correct defaults for region and prefix."""
        for key in SCHEMA_SETUP.schema:
            if str(key) == OPT_REGION:
                assert key.default() == FALLBACK_REGION
