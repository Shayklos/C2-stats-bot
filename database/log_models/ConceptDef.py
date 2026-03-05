"""
Concept definitions for logging.

Each concept represents a reusable log message template with a name and default category.
"""

from dataclasses import dataclass
from typing import Optional
from .CategoryEnum import CategoryEnum


@dataclass(frozen=True)
class ConceptDef:
    """Represents a log concept with template and metadata."""
    template: str
    category: Optional[CategoryEnum] = None


class Concept:
    """Predefined concept constants for common logging scenarios."""
    
    # User operations
    UpdateUser = ConceptDef(
        template="User ~& (id ~¡) updated",
        category=CategoryEnum.GENERAL
    )
    CreateUser = ConceptDef(
        template="User ~& (id ~¡) created",
        category=CategoryEnum.GENERAL
    )
    NameChange = ConceptDef(
        template="User ~& changed name to ~=",
        category=CategoryEnum.NAMECHANGE
    )
    
    # Round operations
    AddRound = ConceptDef(
        template="Added round ~¡ for user ~¡",
        category=CategoryEnum.GENERAL
    )
    ProcessRounds = ConceptDef(
        template="Processed rounds ~¡ to ~¡",
        category=CategoryEnum.GENERAL
    )
    ProcessAllRounds = ConceptDef(
        template="Processed all rounds",
        category=CategoryEnum.GENERAL
    )
