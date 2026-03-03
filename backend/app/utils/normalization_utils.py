import unicodedata
import re 


class NormalizationUtils():

    @staticmethod
    def normalize_text(text) -> str:
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
        text = unicodedata.normalize('NFC', text)
        
        text = text.lower()
        
        text = re.sub(r'[^a-z0-9\s]', '', text)
        
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def normalize_MARC(titulo) -> str:
        patron_articulos = r'^(el |la |los |las |un |una |unos |unas |els |les |the |a |an |le |un |une |des |l[\'’])'
        
        titulo_sin_articulo = re.sub(patron_articulos, '', titulo, flags=re.IGNORECASE)
        
        return titulo_sin_articulo.strip()

    @staticmethod
    def normalize_list(data: list[str] | str | None) -> str:
        """Normalitza llistes o strings a un string separat per comes."""
        if not data:
            return ""
        if isinstance(data, list):
            return ", ".join(data)
        return str(data)
    
    @staticmethod
    def thumbnail_resize(id : str) -> str :
        return f"https://books.google.com/books/publisher/content/images/frontcover/{id}?fife=w800-h1200&source=gbs_api"
