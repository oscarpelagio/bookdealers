from enum import Enum

class ShelfStatus(str, Enum):
    WANT_TO_READ = "want_to_read"
    READING = "reading"
    READ = "read"
    DNF = "did_not_finish" 
