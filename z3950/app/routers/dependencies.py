from fastapi import Depends

from ..clients import Client
from ..services import Service

def get_client(
) -> Client:
    return Client()

def get_service(
    client : Client = Depends(get_client),
) -> Service:
    return Service(client)
