"""Explorer for direct disease–gene associations from the Open Targets Platform."""

__version__ = "0.2.0"

from disease_gene_explorer.explorer import DiseaseGeneExplorer
from disease_gene_explorer.open_targets import OpenTargetsClient, load_curated, load_fixture

__all__ = [
    "DiseaseGeneExplorer",
    "OpenTargetsClient",
    "load_curated",
    "load_fixture",
    "__version__",
]
