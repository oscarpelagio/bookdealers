from enum import Enum


class ReportStatus(str, Enum):
    """Estado del ciclo de vida de un reporte de moderación."""

    OPEN = "OPEN"
    REVIEWING = "REVIEWING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"
