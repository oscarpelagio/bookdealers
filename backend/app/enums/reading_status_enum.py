from enum import Enum


class ReadingStatus(str, Enum):
    """Estado de lectura de un libro en la librería del usuario."""

    WANT_TO_READ = "WANT_TO_READ"
    READING = "READING"
    READ = "READ"
    DNF = "DNF"
