import re

class Z3950Adapter():
            
    def extraer_localizaciones(self, respuesta: str) -> list[dict]:

        texto_respuesta = respuesta.get("response", "")

        bibliotecas_vistas = {}

        ediciones = texto_respuesta.split('Record type: USmarc')
        
        for edicion in ediciones:
            # Buscamos el idioma en el campo 907 $f (por si acaso no hay espacio, usamos \s*)
            lang_match = re.search(r'^907\s+.*\$f\s*([a-zA-Z]+)', edicion, re.MULTILINE)
            idioma = lang_match.group(1).strip() if lang_match else "desconocido"
            
            # 2. Dividimos esa edición concreta en sus diferentes copias (holdings)
            bloques_copias = edicion.split('Data holdings')
            
            # Saltamos el índice 0 porque es la cabecera MARC, las copias empiezan en el 1
            for bloque in bloques_copias[1:]:
                loc_match = re.search(r'localLocation:\s*([^\n]+)', bloque)
                estado_match = re.search(r'publicNote:\s*([^\n]+)', bloque)
                
                if loc_match and estado_match:
                    loc_limpia = loc_match.group(1).split('-')[0].strip()
                    estado = estado_match.group(1).strip()
                    
                    if loc_limpia:
                        clave = (loc_limpia, idioma) # Nuestra nueva clave compuesta
                        
                        # Si no existe la combinación Biblioteca+Idioma, o si el estado actual es 'Available', priorizamos
                        if clave not in bibliotecas_vistas or estado.lower() == 'available':
                            bibliotecas_vistas[clave] = estado
                        
        # 3. Transformamos el diccionario en la lista de diccionarios final
        resultado = []
        for (bib, lang), est in bibliotecas_vistas.items():
            resultado.append({
                "biblioteca": bib,
                "language": lang,
                "estado": est
            })
        
        # 4. Ordenamos primero por biblioteca y luego por idioma
        return sorted(resultado, key=lambda x: (x["biblioteca"], x["language"]))