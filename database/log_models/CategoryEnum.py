from enum import Enum

class CategoryEnum(str, Enum):
    """Enumeration of log entry categories."""
    DISCORD = "Discord"
    ERROR = "Error"
    GENERAL = "General"
    NAMECHANGE = "Namechange"
    TIME = "Time"
