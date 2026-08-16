"""Tests del adaptador del volcat d'Anagrama (sense xarxa)."""

from app.adapters.anagrama_adapter import parse_letter_index, parse_profile

INDEX_SAMPLE = """
<html><body>
<div class="grid gap-10 text-center sm:grid-cols-2 sm:text-left lg:grid-cols-3">
<h2><a href="/autor/abel-max-12" class="text-3xl font-bold">Abel, Max</a></h2>
<h2><a href="/autor/abreu-andrea-2935" class="text-3xl font-bold">Abreu, Andrea</a></h2>
<h2><a href="/autor/azua-felix-de-67" class="text-3xl font-bold">Azúa, Félix de</a></h2>
</div></body></html>
"""

PROFILE_SAMPLE = """
<html><body>
<meta property="og:title" content="Enriquez, Mariana">
<main>
<h1 class="text-center text-4xl font-bold">Enriquez, Mariana</h1>
<div class="relative overflow-hidden">
<img src="https://cms.anagrama-ed.es/uploads/media/autores/0001/30/thumb_29331_autores_big.jpeg">
</div>
<div class="prose prose-lg prose-p:prose-lg!">
<p>Mariana Enriquez (Buenos Aires, 1973) es escritora y periodista.</p>
<p>Su obra se ha traducido a más de veinte idiomas.</p>
</div>
<section>
<h2 class="...">CONTENIDO RELACIONADO</h2>
<div class="swiper">
<div class="swiper-wrapper">
<div class="swiper-slide"><!--[-->
<div class="relative flex flex-col px-4" extractolista="&lt;p&gt;Una conversaci&amp;oacute;n sobre el ejercicio at&amp;aacute;vico de contar un cuento.&lt;/p&gt;">
<a href="/video/poner-voz-a-la-literatura-mariana-enriquez-y-mara-brenner-128?autoplay=true" class="">
<img class="aspect-video" src="https://cms.anagrama-ed.es/uploads/media/videos/0001/30/thumb_29332_videos_big.jpeg" alt="Poner voz a la literatura">
</a>
<a href="/video/poner-voz-a-la-literatura-mariana-enriquez-y-mara-brenner-128" class="flex">
<div class="text-sm tracking-widest text-base-content/65 uppercase">VIDEOS <!----></div>
<div><h2 class="text-2xl font-bold"><span>Poner voz a la literatura: Mariana Enriquez y Mara Brenner</span></h2></div>
<div><div class="text-sm">19/02/2024</div></div>
</a>
</div><!--]--><!----></div>
</div>
</div>
</section>
</main>
</body></html>
"""


def test_parse_letter_index_returns_slugs():
    slugs = parse_letter_index(INDEX_SAMPLE)
    assert slugs == [
        "/autor/abel-max-12",
        "/autor/abreu-andrea-2935",
        "/autor/azua-felix-de-67",
    ]


def test_parse_letter_index_empty():
    assert parse_letter_index("") == []
    assert parse_letter_index("<html></html>") == []


def test_parse_profile_name():
    profile = parse_profile(PROFILE_SAMPLE)
    assert profile.name == "Enriquez, Mariana"


def test_parse_profile_description():
    profile = parse_profile(PROFILE_SAMPLE)
    assert profile.description is not None
    assert "Mariana Enriquez (Buenos Aires, 1973)" in profile.description
    assert "veinte idiomas" in profile.description


def test_parse_profile_image_url():
    profile = parse_profile(PROFILE_SAMPLE)
    assert profile.image_url == (
        "https://cms.anagrama-ed.es/uploads/media/autores/0001/30/"
        "thumb_29331_autores_big.jpeg"
    )


def test_parse_profile_extra_video():
    profile = parse_profile(PROFILE_SAMPLE)
    assert len(profile.extra) == 1
    item = profile.extra[0]
    assert item["tipo"] == "VIDEOS"
    assert item["titulo"] == "Poner voz a la literatura: Mariana Enriquez y Mara Brenner"
    assert item["url"] == "/video/poner-voz-a-la-literatura-mariana-enriquez-y-mara-brenner-128"
    assert item["fecha"] == "19/02/2024"
    assert "contar un cuento" in item["descripcion"]
    assert "videos_big.jpeg" in item["thumbnail"]


def test_parse_profile_without_related_section():
    minimal = PROFILE_SAMPLE.split("<section>")[0] + "</main></body></html>"
    profile = parse_profile(minimal)
    assert profile.name == "Enriquez, Mariana"
    assert profile.extra == []
    assert profile.image_url is not None
