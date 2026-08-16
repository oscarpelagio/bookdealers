import asyncio

class Client():

    async def fetch_book(self, title: str, author: str, url: str, port: int, base: str) -> str:
        commands = "\n".join([
            f"base {base}",
            f'find @and @attr 1=4 @attr 3=3 @attr 4=6 "{title}" @attr 1=1003 @attr 3=3 @attr 4=6 "{author}"',
            "format opac",
            f"show 1+50",
            "exit",
        ])

        print(f'---------> {title} --- {author}')
        
        proc = await asyncio.create_subprocess_exec(
            "yaz-client", f"{url}:{port}",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=commands.encode("utf-8")),
            timeout=30,
        )

        return stdout.decode("utf-8")

    async def fetch_book_brief(self, title: str, author: str, url: str, port: int, base: str) -> str:
        title_attr = f'@attr 1=4 "{title}"' if title else ""
        author_attr = f'@attr 1=1003 "{author}"' if author else ""

        if title and author:
            find_cmd = f"find @and {title_attr} {author_attr}"
        elif title:
            find_cmd = f"find {title_attr}"
        elif author:
            find_cmd = f"find {author_attr}"
        else:
            return ""

        commands = "\n".join([
            f"base {base}",
            find_cmd,
            f"format opac",
            f"show 1+50",
            "exit",
        ])

        proc = await asyncio.create_subprocess_exec(
            "yaz-client", f"{url}:{port}",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=commands.encode("utf-8")),
            timeout=30,
        )
        return stdout.decode("utf-8")

    async def fetch_book_author(self, author: str, url: str, port: int, base: str) -> str:
        if not author:
            return ""
        commands = "\n".join([
            f"base {base}",
            f'find @attr 1=1003 "{author}"',
            f"format opac",
            f"show 1+50",
            "exit",
        ])

        proc = await asyncio.create_subprocess_exec(
            "yaz-client", f"{url}:{port}",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=commands.encode("utf-8")),
            timeout=30,
        )
        return stdout.decode("utf-8")