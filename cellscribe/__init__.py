"""CellScribe — a grounded, agentic assistant for Cell Ontology curation.

Design bet (from evaluating frontier models): LLMs are strong drafters but weak
authorities. So CellScribe grounds every claim in real ontology terms (EBI OLS) and
real papers (Europe PMC), tests markers on data, and hands a curator an
evidence-bearing dossier plus its own critique — never an unverified answer.
"""
from .agent import CuratorAgent
from .models import CurationRequest
from .dossier import CurationDossier

__version__ = "0.1.0"
__all__ = ["CuratorAgent", "CurationRequest", "CurationDossier", "__version__"]
