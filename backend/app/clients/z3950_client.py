from .availability_base_client import AvailabilityBaseClient
import httpx

class Z3950Client(AvailabilityBaseClient):
    
    URL = "http://z3950:8001/search"

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0, 
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
        )
