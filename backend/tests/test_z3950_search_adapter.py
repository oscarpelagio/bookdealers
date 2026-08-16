"""Tests del adaptador de búsqueda Z39.50 (parseo de holdings OPAC)."""

from app.adapters import Z3950SearchAdapter


SAMPLE = """Connecting...OK.
Sent initrequest.
Record type: USmarc
008 240419s        spc          |||| 0 spa||
020    $a 9788420421995
035    $a b15701062
100 1  $a Vilas, Manuel.
245 10 $a Aire nuestro / $c Manuel Vilas.
264  1 $a Barcelona: $b  Alfaguara, $c 2023.
300    $a 419 pàgines ; $c 25 cm.
Data holdings 0
localLocation: ST. ADRIÀ DE B.Sant Adrià
callNumber: N Vil
publicNote: DUE 03-09-26
Data holdings 1
localLocation: STA. COLOMA DE C.Pilarín Bayés
callNumber: N Vil
publicNote: In Transit
[INNOPAC]Record type: OPAC
Record type: USmarc
008 240101s2020    spc           |||| 0 spa||
020    $a 9781234567890
035    $a b22222222
100 1  $a Otra, Autora.
245 10 $a Otro libro / $c Autora Otra.
264  1 $a Madrid: $b  Planeta, $c 2020.
300    $a 200 pàgines ; $c 22 cm.
Data holdings 0
localLocation: BCN.Biblioteca Jaume Fuster
callNumber: N Otr
publicNote: Available
[INNOPAC]Record type: OPAC
"""


def _adapter() -> Z3950SearchAdapter:
    return Z3950SearchAdapter()


def test_response_adapter_counts_holdings_per_record():
    books = _adapter().response_adapter(SAMPLE)

    by_bib = {b.bib_id: b for b in books}
    assert set(by_bib) == {"b15701062", "b22222222"}
    assert by_bib["b15701062"].holdings_count == 2
    assert by_bib["b22222222"].holdings_count == 1


def test_response_adapter_record_without_holdings_is_zero():
    no_holdings = SAMPLE.split("Data holdings 0\nlocalLocation: BCN.Biblioteca Jaume Fuster")[0]
    books = _adapter().response_adapter(no_holdings + "\n[INNOPAC]Record type: OPAC\n")

    by_bib = {b.bib_id: b for b in books}
    assert by_bib["b15701062"].holdings_count >= 2
    assert by_bib["b22222222"].holdings_count == 0
