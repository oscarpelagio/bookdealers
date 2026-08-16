"""Tests del adaptador del volcado de Editorial Tránsito (sin red)."""

from app.adapters.transito_adapter import clean_text, parse_card, parse_authors_page

_CARD_SAMPLE = """
<div class="dfd-team-member layout-01  cr-animate-gen">
<div class="image-wrap"><img decoding="async" src="https://editorialtransito.es/wp-content/uploads/2025/07/Etel-Adan-Bruno-Arbesu-_-BN-400x400.png" alt="Image"  class="team-member-photo " style="border-radius:20px" /><a class="image-custom-link both-title-and-image" href="https://editorialtransito.es/libro/desplazar-el-silencio/" title="Desplazar el silencio" target="_blank"></a></div><div class="content-wrap"><div class="title-wrap"><h5 class="team-member-title " style="font-size: 21px; line-height: 19px; "><a href="https://editorialtransito.es/libro/desplazar-el-silencio/" title="Desplazar el silencio" target="_blank">ETEL ADNAN</a></h5><div class="team-member-subtitle subtitle" style="font-size: 16px; line-height: 17px; font-style:italic; ">Desplazar el silencio</div><div class="wrap-delimiter"><div class="delimiter" style="width:100px;border-width:1px;border-color:#a8a8a8"></div></div></div><div class="team-member-description" style="font-size: 13px; line-height: 16px; "><b>Etel Adnan</b> nació en Beirut, Líbano, en 1925. Estudió Filosofía en la Sorbona, Berkeley y Harvard, y ejerció como profesora en el Dominican College de San Rafael, California. Desde los años sesenta combinó escritura, pensamiento y arte visual. Influida por su activismo contra la Guerra de Vietnam, empezó a escribir poesía y se consideró «una poeta estadounidense». Es autora de poesía, ensayo y teatro; destacan <i>Journey to Mount Tamalpais, The Arab Apocalypse</i> y la novela <i>Sitt Marie-Rose</i>, traducida a más de diez idiomas. En 2014 recibió la Orden de las Artes y las Letras. Falleció en París en 2021.</div></div></div>
<div class="dfd-spacer-module"  data-units="px"></div>
"""

_PAGE_SAMPLE = """
<html><body>
<p>whole header etc</p>
<div class="dfd-team-member layout-01 ">
<div class="image-wrap"><img src="https://editorialtransito.es/wp-content/uploads/2023/09/KatixaAgirre-\u00a9DonnaSalama-400x400.jpg" alt="Image"  class="team-member-photo" /></div><div class="content-wrap"><div class="title-wrap"><h5 class="team-member-title "><a href="https://editorialtransito.es/libro/las-madres-no/" >KATIXA AGIRRE</a></h5></div><div class="team-member-description" style=""><b>Katixa Agirre</b> (Vitoria, 1981) es escritora en lengua vasca. Tercera novela <i>De nuevo centauro</i>.</div></div></div>
<div class="dfd-spacer-module" ></div>
<div class="dfd-team-member layout-01  cr-animate-gen">
<div class="image-wrap"><img src="https://editorialtransito.es/wp-content/uploads/2022/03/c-Edith-Cota-1-blackwhite-400x400.jpg" class="team-member-photo" /></div><div class="content-wrap"><div class="title-wrap"><h5 class="team-member-title "><a href="https://editorialtransito.es/libro/basura/" >SYLVIA AGUILAR Z\u00c9LENY</a></h5></div><div class="team-member-description" style=""><b>Sylvia Aguilar Z\u00e9leny</b> (M\u00e9xico, 1973).</div></div></div>
<div class="dfd-spacer-module" ></div>
</body></html>
"""


def test_clean_text_strips_tags_and_entities():
    assert clean_text("<p><b>one</b> two &amp; three</p>") == "one two & three"
    assert clean_text("<p>   <b></b>  </p>") is None
    assert clean_text("") is None


def test_parse_card_full():
    profile = parse_card(_CARD_SAMPLE)
    assert profile is not None
    assert profile.name == "Etel Adnan"
    assert profile.description is not None
    assert profile.description.startswith("Etel Adnan nació en Beirut")
    assert "Falleció en París en 2021." in profile.description
    assert profile.image_url == (
        "https://editorialtransito.es/wp-content/uploads/2025/07/"
        "Etel-Adan-Bruno-Arbesu-_-BN.png"
    )


def test_parse_card_name_fallback_title_case():
    block = _CARD_SAMPLE.replace(
        '<b>Etel Adnan</b> nació', '<span>sin bold</span> hace'
    ).replace('ETEL ADNAN', 'ETEL ADNAN')
    profile = parse_card(block)
    assert profile is not None
    assert profile.name == "Etel Adnan"


def test_parse_card_without_header():
    assert parse_card("<div><p>no team member</p></div>") is None


def test_parse_authors_page_multiple():
    profiles = parse_authors_page(_PAGE_SAMPLE)
    assert len(profiles) == 2
    assert profiles[0].name == "Katixa Agirre"
    assert profiles[1].name == "Sylvia Aguilar Zéleny"
    assert profiles[1].image_url == (
        "https://editorialtransito.es/wp-content/uploads/2022/03/"
        "c-Edith-Cota-1-blackwhite.jpg"
    )


def test_parse_authors_page_empty():
    assert parse_authors_page("") == []
    assert parse_authors_page("<html></html>") == []