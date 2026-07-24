"""
Service for checking availability in the ALADI catalog via Z39.50.
"""

from app.services import AvailabilityBaseService

class Z3950Service(AvailabilityBaseService):
    SERVICE_NAME = "z3950"
