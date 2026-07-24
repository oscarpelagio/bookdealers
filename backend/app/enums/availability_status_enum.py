from enum import Enum

class AvailabilityStatusEnum(str, Enum):
    AVAILABLE = "available"
    BORROW = "borrow"
    LOST = "lost"
    LIB_USE_ONLY = "lib use only"
    ON_DEMAND = "on_demand"
    AVAILABLE_IN_2_3_DAYS = "available_in_2_3_days"
    UNKNOWN = "unknown"
