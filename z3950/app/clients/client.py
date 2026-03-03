import asyncio

class Client():

    def __init__(
        self, 
        host: str,
        port: int,
        base: str
    ):
        self.host = host
        self.port = port
        self.base = base

    async def fetch_book(self, title: str, author: str) -> str:
        commands = "\n".join([
            f"base {self.base}",
            f'find @and @attr 1=4 @attr 3=3 @attr 4=6 "{title}" @attr 1=1003 @attr 3=3 @attr 4=6 "{author}"',
            "format opac",
            f"show 1+50",
            "exit",
        ])
        
        proc = await asyncio.create_subprocess_exec(
            "yaz-client", f"{self.host}:{self.port}",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=commands.encode("utf-8")),
            timeout=30,
        )

        return stdout.decode("utf-8")
