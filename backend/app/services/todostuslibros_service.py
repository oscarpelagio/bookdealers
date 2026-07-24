"""
Servei per consultar disponibilitat a Todostuslibros.
"""

from app.services import AvailabilityBaseService


class TodostuslibrosService(AvailabilityBaseService):
    SERVICE_NAME = "todostuslibros"
