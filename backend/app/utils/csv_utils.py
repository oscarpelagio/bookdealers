import csv
import io

from fastapi import UploadFile

class CsvUtils:

    @staticmethod
    async def parse_goodreads_book(file: UploadFile) -> list[dict]:
        file_bytes = await file.read()
        stream = io.StringIO(file_bytes.decode("utf-8"))
        reader = csv.DictReader(stream)        
        searchs = []
        for row in reader:
            searchs.append({
            "title": row.get("Title"),
            "author": row.get("Author"),
            "my_rating": row.get("My Rating"),
            "average_rating": row.get("Average Rating"),
            "publisher": row.get("Publisher"),
            "number_of_pages": row.get("Number of Pages"),
            "year_published": row.get("Year Published"),
            "original_publication_year": row.get("Original Publication Year"),
            "date_read": row.get("Date Read"),
            "date_added": row.get("Date Added"),
            "bookshelves": row.get("Bookshelves"),
            "bookshelves_with_positions": row.get("Bookshelves with positions"),
            "exclusive_shelf": row.get("Exclusive Shelf"),
            "my_review": row.get("My Review"),
            "spoiler": row.get("Spoiler"),
            "private_notes": row.get("Private Notes")                 
            })
        return searchs
