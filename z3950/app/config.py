SOURCES = {
    # catàleg de la diputació de barcelona
    "aladi": {"host": "aladi.diba.cat", "port":210, "base":"INNOPAC"},
    # catàleg de girona, lleida i tarragona
    "argus": {"host": "elmeuargus.biblioteques.gencat.cat", "port":210, "base":"INNOPAC"},
    # catàleg de les illes balears
    "cabib": {"host": "cabib.uib.es", "port":210, "base":"INNOPAC"}
}

HOST = SOURCES["aladi"]["host"]
PORT = SOURCES["aladi"]["port"]
BASE = SOURCES["aladi"]["base"]
