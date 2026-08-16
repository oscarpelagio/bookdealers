"""Tests del adaptador del blog de La Central (sin red)."""

from app.adapters.la_central_adapter import (
    parse_article,
    parse_listing,
    parse_article,
)


LISTING_SAMPLE = """
<html><body>
<div id="main">
<div class="col-12 blog-articulo">
  <div class="row">
    <div class="col-auto">
      <div class="blog-articulo__imagen">
        <a href="/blog/eclipsis-192672">
          <img alt="Eclipsis" src="https://cloudflare.lacentral.com/blog-imgs/portada.jpg"/>
        </a>
      </div>
    </div>
    <div class="col-sm">
      <div class="blog-articulo__info">
        <p class="blog-articulo__tipo">Temàtica</p>
        <h3 class="blog-articulo__titulo">Eclipsis</h3>
        <h4 class="blog-articulo__subtitulo">"Quedant tot escur com si fos de nit"</h4>
        <p class="blog-articulo__autor">Per Roger Fernández</p>
        <p>Aquest estiu la dansa dels astres ens ofereix una situació.</p>
        <p><a href="/blog/eclipsis-192672">Llegir més</a></p>
      </div>
    </div>
  </div>
</div>
<div class="col-12 blog-articulo">
  <div class="row">
    <div class="col-auto">
      <div class="blog-articulo__imagen">
        <a href="/blog/bostonianes-safiques-i-una-mica-mes--192568">
          <img alt="Bostonianes" src="https://cloudflare.lacentral.com/blog-imgs/b.jpg"/>
        </a>
      </div>
    </div>
    <div class="col-sm">
      <div class="blog-articulo__info">
        <p class="blog-articulo__tipo">Temàtica</p>
        <h3 class="blog-articulo__titulo">Bostonianes, sàfiques i una mica més</h3>
        <p class="blog-articulo__autor">Per María José Pérez</p>
        <p>Les condicions culturals, socials i polítiques al llarg de la història.</p>
        <p><a href="/blog/bostonianes-safiques-i-una-mica-mes--192568">Llegir més</a></p>
      </div>
    </div>
  </div>
</div>
</div>
</body></html>
"""

ARTICLE_SAMPLE = """
<html><body>
<main id="main">
<section id="articulo">
  <div class="container">
    <div class="row" id="blog-header"><div class="col-12"><h1 class="titulo">Les nostres recomanacions i propostes</h1></div></div>
    <div class="row">
      <div class="col mt-4 order-0">
        <div class="d-flex my-4" id="articulo__hero">
          <picture><img alt="Eclipsis" class="w-100 h-100" src="https://cloudflare.lacentral.com/blog-imgs/hero.jpg"/></picture>
        </div>
        <p class="blog-articulo__tipo">Temàtica</p>
        <h3 class="blog-articulo__titulo">Eclipsis</h3>
        <h4 class="blog-articulo__subtitulo">"Quedant tot escur com si fos de nit"</h4>
        <h4 class="blog-articulo__subtitulo" style="font-size: 1.3rem;">«Un fenomen com aquest.»</h4>
        <p><span class="blog-articulo__autor">Per Roger Fernández</span><br/>26.7.2026</p>
        <div class="a2a_kit"><a>Compartir</a></div>
      </div>
    </div>
    <div class="row">
      <div class="col">
        <div class="blog-articulo__contenido">
          <p>Aquest estiu la dansa dels astres.</p>
          <p>Hi ha diferents tipus d'eclipsis.</p>
          <br/><br/>
        </div>
        <div class="row no-gutters">
          <div class="libro">
            <div class="libro-hover">
              <img alt="Luna y Sol" class="libro__portada" src="https://www.lacentral.com/atril/9791387709945.jpg"/>
              <div class="libro-hover__overlay">
                <div class="libro__info">
                  <span class="libro__autor">Abadía, Ximo</span>
                  <span class="libro__autor">Abadía, Ximo (Ilustrador/a)</span>
                  <a class="libro__titulo" href="/abadia-ximo/luna-y-sol/9791387709945">Luna y Sol</a>
                  <span class="libro__precio">19,90 €</span>
                </div>
              </div>
            </div>
          </div>
          <div class="libro">
            <div class="libro-hover">
              <div class="libro-hover__overlay">
                <div class="libro__info">
                  <span class="libro__autor">Eclipses</span>
                  <a class="libro__titulo" href="/">Brasero, Roberto</a>
                  <span class="libro__precio">20,90 €</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
</main>
</body></html>
"""


def test_parse_listing_cards():
    cards = parse_listing(LISTING_SAMPLE)
    assert len(cards) == 2
    assert cards[0].slug == "eclipsis-192672"
    assert cards[0].titulo == "Eclipsis"
    assert cards[0].subtitulo == '"Quedant tot escur com si fos de nit"'
    assert cards[0].autor == "Roger Fernández"
    assert "Aquest estiu" in cards[0].intro
    assert cards[0].url == "https://www.lacentral.com/blog/eclipsis-192672"

    assert cards[1].titulo == "Bostonianes, sàfiques i una mica més"
    assert cards[1].autor == "María José Pérez"


def test_parse_listing_empty():
    assert parse_listing("") == []
    assert parse_listing("<html></html>") == []


def test_parse_article_full():
    art = parse_article(ARTICLE_SAMPLE, "eclipsis-192672")
    assert art.titulo == "Eclipsis"
    assert art.subtitulo == '"Quedant tot escur com si fos de nit"'
    assert art.intro == "«Un fenomen com aquest.»"
    assert art.autor == "Roger Fernández"
    assert art.fecha == "26.7.2026"
    assert art.tipo == "Temàtica"
    assert art.portada_url == "https://cloudflare.lacentral.com/blog-imgs/hero.jpg"
    assert "dansa dels astres" in art.cuerpo
    assert len(art.libros) == 2


def test_parse_article_libros():
    art = parse_article(ARTICLE_SAMPLE, "eclipsis-192672")
    assert art.libros[0].titulo == "Luna y Sol"
    assert art.libros[0].autor == "Abadía, Ximo"
    assert art.libros[0].posicion == 0
    assert art.libros[1].posicion == 1