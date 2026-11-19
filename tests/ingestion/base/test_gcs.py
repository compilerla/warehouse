"""Tests for GCS upload and local fallback."""

import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from ingestion.base import gcs


class TestGenerateBlobName:
    """Tests for _generate_blob_name helper."""

    def _patch_datetime(self, dt_value):
        """Replace gcs.datetime with a MagicMock returning a fixed value."""
        fake_dt = MagicMock()
        fake_dt.now.return_value = dt_value
        return patch.object(gcs, "datetime", fake_dt)

    def test_format(self):
        """Test the blob name follows the expected pattern."""
        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with self._patch_datetime(fixed_dt):
            result = gcs._generate_blob_name("toggl", "timesheets.csv", "compiler-data-lake")
        assert result == "compiler-data-lake/toggl/2026/11/10/timesheets_20261110T143000.csv"

    def test_jsonl_extension(self):
        """Test JSONL files get the same pattern."""
        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with self._patch_datetime(fixed_dt):
            result = gcs._generate_blob_name("toggl", "projects.jsonl")
        assert result.endswith(".jsonl")
        assert "projects_" in result

    def test_custom_prefix(self):
        """Test custom prefix is used."""
        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with self._patch_datetime(fixed_dt):
            result = gcs._generate_blob_name("toggl", "file.csv", prefix="my-bucket")
        assert result.startswith("my-bucket/")


class TestResolveBucket:
    """Tests for _resolve_bucket helper."""

    def test_param_overrides_env(self):
        """Test explicit param takes priority over env var."""
        with patch.dict(os.environ, {"BUCKET_NAME": "env-bucket"}):
            result = gcs._resolve_bucket("param-bucket")
        assert result == "param-bucket"

    def test_env_var_used_when_param_none(self):
        """Test env var is used when param is None."""
        with patch.dict(os.environ, {"BUCKET_NAME": "env-bucket"}):
            result = gcs._resolve_bucket(None)
        assert result == "env-bucket"

    def test_none_when_nothing_set(self):
        """Test returns None when neither is set."""
        with patch.dict(os.environ, {}, clear=True):
            result = gcs._resolve_bucket(None)
        assert result is None

    def test_param_empty_string_fallback(self):
        """Test empty string param is treated as None (uses env)."""
        with patch.dict(os.environ, {"BUCKET_NAME": "env-bucket"}):
            result = gcs._resolve_bucket("")
        # Empty string is falsy in Python, so it falls back to env
        assert result == "env-bucket"


class TestInjectPullDate:
    """Tests for _inject_pull_date helper."""

    def test_csv_injects_column(self):
        """Test CSV data gets pull_date column."""
        csv_data = "id,amount\n1,100\n2,200\n"
        result = gcs._inject_pull_date(csv_data, "test.csv", "2026-11-10")
        assert "pull_date" in result
        assert "2026-11-10" in result

    def test_csv_injects_column_dataframe(self):
        """Test CSV pull_date is actually added to the DataFrame."""
        csv_data = "id,amount\n1,100\n2,200\n"
        result = gcs._inject_pull_date(csv_data, "test.csv", "2026-11-10")
        df = pd.read_csv(io.StringIO(result))
        assert "pull_date" in df.columns
        assert all(df["pull_date"] == "2026-11-10")

    def test_jsonl_injects_key(self):
        """Test JSONL data gets pull_date key."""
        jsonl_data = '{"id": 1, "amount": 100}\n{"id": 2, "amount": 200}\n'
        result = gcs._inject_pull_date(jsonl_data, "test.jsonl", "2026-11-10")
        assert '"pull_date": "2026-11-10"' in result

    def test_unknown_format_unchanged(self):
        """Test unknown formats return data unchanged."""
        data = "some data"
        result = gcs._inject_pull_date(data, "test.txt", "2026-11-10")
        assert result == data


class TestWriteToLocal:
    """Tests for _write_to_local helper."""

    def test_creates_nested_dirs(self, tmp_path):
        """Test that nested directories are created."""
        output_dir = str(tmp_path / "output")
        result = gcs._write_to_local(output_dir, "compiler-data-lake/toggl/2026/11/10/file.csv", "data")
        expected = Path(output_dir) / "compiler-data-lake" / "toggl" / "2026" / "11" / "10" / "file.csv"
        assert expected.exists()
        assert result == str(expected)

    def test_returns_file_path(self, tmp_path):
        """Test that the function returns the file path."""
        output_dir = str(tmp_path / "output")
        result = gcs._write_to_local(output_dir, "toggl/data.csv", "data")
        assert result == str(Path(output_dir) / "toggl" / "data.csv")

    def test_overwrites_existing_file(self, tmp_path):
        """Test that existing files are overwritten."""
        output_dir = str(tmp_path / "output")
        path = Path(output_dir) / "toggl" / "file.csv"
        path.parent.mkdir(parents=True)
        path.write_text("old content")

        gcs._write_to_local(output_dir, "toggl/file.csv", "new data")
        assert path.read_text() == "new data"


class TestUploadToStorage:
    """Tests for upload_to_storage (GCS or local fallback)."""

    def _patch_datetime(self, dt_value):
        """Replace gcs.datetime with a MagicMock returning a fixed value."""
        fake_dt = MagicMock()
        fake_dt.now.return_value = dt_value
        return patch.object(gcs, "datetime", fake_dt)

    def test_gcs_when_bucket_name_env_set(self, mocker):
        """Test GCS is used when BUCKET_NAME env var is set."""
        mock_bucket = mocker.MagicMock()
        mock_blob = mocker.MagicMock()
        mock_client_cls = mocker.patch.object(gcs.storage, "Client")
        mock_client_cls.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with patch.dict(os.environ, {"BUCKET_NAME": "test-bucket"}), self._patch_datetime(fixed_dt):
            result = gcs.upload_to_storage("test data", "toggl", "timesheets.csv")

        assert result.startswith("compiler-data-lake/toggl/")
        mock_bucket.blob.assert_called_once()
        mock_blob.upload_from_string.assert_called_once()

    def test_gcs_when_bucket_param_provided(self, mocker):
        """Test GCS is used when bucket_name param overrides env."""
        mock_bucket = mocker.MagicMock()
        mock_blob = mocker.MagicMock()
        mock_client_cls = mocker.patch.object(gcs.storage, "Client")
        mock_client_cls.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with patch.dict(os.environ, {}, clear=True), self._patch_datetime(fixed_dt):
            result = gcs.upload_to_storage("test data", "toggl", "timesheets.csv", bucket_name="param-bucket")

        assert result.startswith("compiler-data-lake/toggl/")
        mock_bucket.blob.assert_called_once()

    def test_gcs_param_overrides_env(self, mocker):
        """Test bucket_name param overrides BUCKET_NAME env var."""
        mock_bucket = mocker.MagicMock()
        mock_blob = mocker.MagicMock()
        mock_client_cls = mocker.patch.object(gcs.storage, "Client")
        mock_client_cls.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with patch.dict(os.environ, {"BUCKET_NAME": "env-bucket"}), self._patch_datetime(fixed_dt):
            gcs.upload_to_storage("test data", "toggl", "timesheets.csv", bucket_name="param-bucket")

        # Verify the param bucket name was used (not the env var bucket)
        mock_bucket = mock_client_cls.return_value.bucket.return_value
        call_args = mock_client_cls.return_value.bucket.call_args
        assert call_args[0][0] == "param-bucket"

    def test_local_when_no_bucket_set(self, tmp_path):
        """Test local filesystem is used when no bucket is configured."""
        output_dir = str(tmp_path / "output")
        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with patch.dict(os.environ, {"OUTPUT_DIR": output_dir}), self._patch_datetime(fixed_dt):
            result = gcs.upload_to_storage("test data", "toggl", "timesheets.csv")
        expected = Path(output_dir) / "compiler-data-lake" / "toggl" / "2026" / "11" / "10"
        assert Path(result).is_relative_to(expected)
        assert Path(result).suffix == ".csv"

    def test_local_default_path_when_no_output_dir(self, tmp_path):
        """Test local uses default path when OUTPUT_DIR not set."""
        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with patch.dict(os.environ, {}, clear=True), self._patch_datetime(fixed_dt):
            result = gcs.upload_to_storage("test data", "toggl", "timesheets.csv")
        assert "/tmp/warehouse-ingestion" in result

    def test_pull_date_used_when_provided(self, tmp_path):
        """Test that a provided pull_date is used instead of today."""
        output_dir = str(tmp_path / "output")
        with patch.dict(os.environ, {"OUTPUT_DIR": output_dir}):
            result = gcs.upload_to_storage("test data", "toggl", "data.csv", pull_date="2026-01-01")
        assert Path(result).exists()

    def test_custom_prefix_in_local(self, tmp_path):
        """Test that custom prefix is used in local mode."""
        output_dir = str(tmp_path / "output")
        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with patch.dict(os.environ, {"OUTPUT_DIR": output_dir}), self._patch_datetime(fixed_dt):
            result = gcs.upload_to_storage("test data", "toggl", "file.csv", prefix="custom-prefix")
        assert "custom-prefix" in result

    def test_csv_data_injected_with_pull_date(self, tmp_path):
        """Test that CSV data gets pull_date column when writing locally."""
        output_dir = str(tmp_path / "output")
        csv_data = "id,amount\n1,100\n2,200\n"
        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with patch.dict(os.environ, {"OUTPUT_DIR": output_dir}), self._patch_datetime(fixed_dt):
            result = gcs.upload_to_storage(csv_data, "toggl", "data.csv", pull_date="2026-11-10")
        written = Path(result).read_text()
        assert "pull_date" in written
        assert "2026-11-10" in written

    def test_jsonl_data_injected_with_pull_date(self, tmp_path):
        """Test that JSONL data gets pull_date key when writing locally."""
        output_dir = str(tmp_path / "output")
        jsonl_data = '{"id": 1}\n{"id": 2}\n'
        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with patch.dict(os.environ, {"OUTPUT_DIR": output_dir}), self._patch_datetime(fixed_dt):
            result = gcs.upload_to_storage(jsonl_data, "toggl", "data.jsonl", pull_date="2026-11-10")
        written = Path(result).read_text()
        assert '"pull_date": "2026-11-10"' in written

    def test_gcs_csv_data_injected(self, mocker):
        """Test that CSV data gets pull_date when uploading to GCS."""
        mock_bucket = mocker.MagicMock()
        mock_blob = mocker.MagicMock()
        mock_client_cls = mocker.patch.object(gcs.storage, "Client")
        mock_client_cls.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        csv_data = "id,amount\n1,100\n2,200\n"
        fixed_dt = gcs.datetime(2026, 11, 10, 14, 30, 0, tzinfo=gcs.UTC)
        with patch.dict(os.environ, {"BUCKET_NAME": "test-bucket"}), self._patch_datetime(fixed_dt):
            _ = gcs.upload_to_storage(csv_data, "toggl", "data.csv", pull_date="2026-11-10")

        call_args = mock_blob.upload_from_string.call_args
        uploaded_data = call_args[0][0]
        assert "pull_date" in uploaded_data
        assert "2026-11-10" in uploaded_data
