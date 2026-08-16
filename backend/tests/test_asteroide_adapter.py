"""Tests del adaptador de Libros del Asteroide (sin red)."""

from app.adapters.asteroide_adapter import (
    clean_text,
    parse_authors_index,
    parse_profile,
)

INDEX_SAMPLE = """
<html><body>
<div class="cbp-item letter-A">
<a class="cbp-caption" href="https://librosdelasteroide.com/autor/angelou-maya">
<div class="author-photo" style="background-image: url('...')"></div>
<div class="py-3 min-title-height-authors">
<h4 class="font-17 text-dark">Angelou, Maya</h4>
</div>
</a>
</div>
<div class="cbp-item letter-S">
<a class="cbp-caption" href="https://librosdelasteroide.com/autor/lucia-solla-sobral">
<div class="author-photo" style="background-image: url('...')"></div>
<div class="py-3 min-title-height-authors">
<h4 class="font-17 text-dark">Solla Sobral, Luc\u00eda</h4>
</div>
</a>
</div>
</body></html>
"""

PROFILE_SAMPLE = """
<html><body>
<title>Lucía Solla Sobral - Libros del Asteroide</title>
<main>
<img class="img-fluid mb-8" src="https://librosdelasteroide.com/images/authors/20250707120440.jpg" alt="Lucía">
<h1 class="font-size-7 ont-weight-medium mt-2 mb-3 pb-1">Lucía Solla Sobral</h1>
<p class="mb-0"><p><b>Lucía Solla Sobral</b><span> (Marín, 1989) vive actualmente en Oviedo.</span></p></p>
</main>
</body></html>
"""


def test_clean_text():
    assert clean_text("<p><b>a</b> b</p>") == "a b"
    assert clean_text("  \n  ") is None
    assert clean_text("") is None


def test_parse_authors_index_entries():
    entries = parse_authors_index(INDEX_SAMPLE)
    assert len(entries) == 2
    assert entries[0].slug == "angelou-maya"
    assert entries[0].name == "Angelou, Maya"
    assert entries[1].slug == "lucia-solla-sobral"
    assert entries[1].name == "Solla Sobral, Lucía"


def test_parse_authors_index_empty():
    assert parse_authors_index("") == []
    assert parse_authors_index("<html></html>") == []


def test_parse_profile_full():
    profile = parse_profile(PROFILE_SAMPLE)
    assert profile.name == "Lucía Solla Sobral"
    assert profile.image_url == (
        "https://librosdelasteroide.com/images/authors/20250707120440.jpg"
    )
    assert profile.description is not None
    assert "Marín, 1989" in profile.description


def test_parse_profile_empty():
    profile = parse_profile("")
    assert profile.name == ""
    assert profile.image_url is None
    assert profile.description is None