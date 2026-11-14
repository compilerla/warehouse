import importlib
import pkgutil
from dataclasses import dataclass


@dataclass
class PullConfig:
    """Configuration for a single ingestion pull.

    Attributes:
        source: Name of the ingestion source (e.g., "toggl").
        start_date: Start date string (absolute date or relative keyword).
        end_date: End date string (absolute date or relative keyword).
        output_bucket: GCS bucket name for output files.
        prefix: GCS prefix (default: "compiler-data-lake").
    """

    source: str
    start_date: str
    end_date: str
    output_bucket: str
    prefix: str = "compiler-data-lake"


class Puller:
    """Abstract base class for ingestion sources.

    Subclasses must define a ``source_name`` class attribute and implement
    ``pull()`` to fetch data from a specific source, transform it, and upload
    it to GCS (or local filesystem).

    Subclasses are auto-discovered at import time so no manual registration
    is needed — just add a new module with a ``Puller`` subclass.
    """

    source_name: str

    def pull(self, source: str, start_date: str | None = None, end_date: str | None = None) -> list[str]:
        """Pull data from the source and return list of uploaded GCS paths.

        Args:
            source: Name of the ingestion source.
            start_date: Start date (override CLI/env defaults).
            end_date: End date (override CLI/env defaults).

        Returns:
            List of GCS paths for uploaded files.

        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement pull()")


def discover_pullers() -> dict[str, type[Puller]]:
    """Discover all Puller subclasses across the ingestion package.

    Walks all submodules of ``ingestion`` and collects classes that are
    direct (or indirect) subclasses of ``Puller``.  Modules that cannot be
    imported are silently skipped so that optional sources (e.g. ones that
    depend on packages that may not be installed) don't break the CLI.

    Returns:
        Dict mapping ``source_name`` to the Puller subclass.
    """
    results: dict[str, type[Puller]] = {}

    for importer, mod_name, is_pkg in pkgutil.walk_packages(
        path=importlib.import_module("ingestion").__path__,
        prefix="ingestion.",
        onerror=lambda _: None,
    ):
        try:
            module = importlib.import_module(mod_name)
        except ImportError:
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not (isinstance(attr, type) and issubclass(attr, Puller) and attr is not Puller):
                continue

            source = getattr(attr, "source_name", None)
            if source:
                results[source] = attr

    return results
