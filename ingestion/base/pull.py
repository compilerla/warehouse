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

    def pull(
        self,
        source: str,
        start_date: str | None = None,
        end_date: str | None = None,
        bucket_name: str | None = None,
    ) -> list[str]:
        """Pull data from the source and return list of uploaded GCS paths.

        Args:
            source: Name of the ingestion source.
            start_date: Start date (override CLI/env defaults).
            end_date: End date (override CLI/env defaults).
            bucket_name: GCS bucket name (overrides BUCKET_NAME env var).

        Returns:
            List of GCS paths for uploaded files.

        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement pull()")


def _collect_pullers(module: object) -> dict[str, type["Puller"]]:
    """Collect Puller subclasses from a single module.

    Args:
        module: A Python module object (e.g. from ``importlib.import_module``).

    Returns:
        Dict mapping ``source_name`` to the Puller subclass found in the module.
    """
    results: dict[str, type["Puller"]] = {}
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if not (isinstance(attr, type) and issubclass(attr, Puller) and attr is not Puller):
            continue

        source = getattr(attr, "source_name", None)
        if source:
            results[source] = attr

    return results


def discover_pullers(
    base_package: str = "ingestion",
    on_error: callable | None = None,
) -> dict[str, type[Puller]]:
    """Discover all Puller subclasses across a package.

    Walks all submodules of the given package and collects classes that are
    subclasses of ``Puller``.  Modules that cannot be imported are silently
    skipped so that optional sources (e.g. ones that depend on packages
    that may not be installed) don't break the CLI.

    Args:
        base_package: The root package to scan (default: ``"ingestion"``).
        on_error: Optional callback invoked when a module fails to import.

    Returns:
        Dict mapping ``source_name`` to the Puller subclass.
    """
    results: dict[str, type[Puller]] = {}
    root = importlib.import_module(base_package)

    for importer, mod_name, is_pkg in pkgutil.walk_packages(
        path=root.__path__,
        prefix=f"{base_package}.",
        onerror=lambda err: on_error(err) if on_error else None,
    ):
        try:
            module = importlib.import_module(mod_name)
        except ImportError:
            continue

        results.update(_collect_pullers(module))

    return results
