"""
Servei per consultar disponibilitat al catàleg ALADI via Z39.50.
"""

from app.services import AvailabilityBaseService

class EBiblioService(AvailabilityBaseService):
    SERVICE_NAME = "ebiblio"
