"""Tests del adaptador del volcat de Blackie Books (sense xarxa)."""

from app.adapters.blackie_adapter import (
    parse_authors_index,
    parse_media_url,
    parse_profile,
)

INDEX_SAMPLE = [
    {"slug": "gloria-fuertes", "title": {"rendered": "Gloria Fuertes"}},
    {"slug": "a-f-harrold", "title": {"rendered": "A. F. Harrold"}},
    {
        "slug": "andrew-oneill",
        "title": {"rendered": "Andrew O&#8217;Neill"},
    },
    {"slug": "gloria-fuertes", "title": {"rendered": "Gloria Fuertes"}},
    {"slug": "", "title": {"rendered": ""}},
]

PROFILE_SAMPLE = {
    "slug": "gloria-fuertes",
    "title": {"rendered": "Gloria Fuertes"},
    "content": {
        "rendered": (
            "<p style=\"text-align: justify;\"><strong>Gloria Fuertes</strong> "
            "(1917-1998). Madrile&ntilde;a. Se le fueron cayendo los poemas del "
            "cuerpo.</p>\n<p>Segunda par&#224;graf&raquo;</p>"
        )
    },
    "_links": {
        "wp:featuredmedia": [{"href": "https://blackiebooks.org/wp-json/wp/v2/media/10686"}]
    },
}

MEDIA_SAMPLE = {
    "id": 10686,
    "source_url": "https://blackiebooks.org/wp-content/uploads/2024/07/gloria-fuertes-min-1.jpg",
}


def test_parse_authors_index_dedup_skips_empty():
    slugs = parse_authors_index(INDEX_SAMPLE)
    assert slugs == ["gloria-fuertes", "a-f-harrold", "andrew-oneill"]


def test_parse_authors_index_empty():
    assert parse_authors_index([]) == []


def test_parse_profile_basic():
    profile = parse_profile(PROFILE_SAMPLE)
    assert profile.name == "Gloria Fuertes"
    assert profile.media_id == 10686


def test_parse_profile_entities_and_description():
    profile = parse_profile(PROFILE_SAMPLE)
    assert profile.description is not None
    assert "Gloria Fuertes (1917-1998)" in profile.description
    assert "Madrileña" in profile.description
    assert "poemas del cuerpo" in profile.description
    assert "Segunda paràgraf»" in profile.description


def test_parse_profile_without_media():
    item = dict(PROFILE_SAMPLE)
    item.pop("_links")
    profile = parse_profile(item)
    assert profile.name == "Gloria Fuertes"
    assert profile.media_id is None
    assert profile.image_url is None


def test_parse_profile_empty():
    profile = parse_profile({})
    assert profile.name == ""


def test_parse_media_url():
    assert parse_media_url(MEDIA_SAMPLE) == MEDIA_SAMPLE["source_url"]
    assert parse_media_url({}) is None


def test_parse_profile_title_html_clean():
    item = {"title": {"rendered": "Tom Morris &#8211; Matt Morris (eds.)"},
            "content": {"rendered": ""}}
    profile = parse_profile(item)
    assert profile.name == "Tom Morris – Matt Morris (eds.)"