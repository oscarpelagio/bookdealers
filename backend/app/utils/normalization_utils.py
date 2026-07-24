import unicodedata
import re 


class NormalizationUtils():

    @staticmethod
    def normalize_text(text) -> str:
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
        text = unicodedata.normalize('NFC', text)
        text = text.lower()
        text = text.replace('-', ' ')
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def normalize_MARC(title) -> str:
        article_pattern = r'^(el |la |los |las |un |una |unos |unas |els |les |the |a |an |le |un |une |des |l[\'’])'
        
        title_without_article = re.sub(article_pattern, '', title, flags=re.IGNORECASE)
        
        return title_without_article.strip()

    @staticmethod
    def normalize_list(data: list[str] | str | None) -> str:
        """Normalize lists or strings into a comma-separated string."""
        if not data:
            return ""
        if isinstance(data, list):
            return ", ".join(data)
        return str(data)
    
    @staticmethod
    def thumbnail_resize(id : str) -> str :
        return f"https://books.google.com/books/publisher/content/images/frontcover/{id}?fife=w800-h1200&source=gbs_api"
