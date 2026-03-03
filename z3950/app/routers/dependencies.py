from fastapi import Depends

from ..clients import Client
from ..services import Service
from ..config import ALADI_HOST, ALADI_PORT, DATABASE


def get_client(
) -> Client:
    return Client(ALADI_HOST, ALADI_PORT, DATABASE)

def get_service(
    client : Client = Depends(get_client),
) -> Service:
    return Service(client)
