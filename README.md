# Xafapins · App feta per Dr.Sopes

Visor orientativo de meteorología y setas para las 19 regiones de España. Interfaz en catalán, 24 especies y OpenStreetMap como único mapa base.

## Cambios de esta versión

- Retícula **visual de 250 m** al acercarse (zoom 12 o superior), generada solo para el área visible. El cálculo permanece a **1 km**; ni la retícula ni la interpolación añaden precisión a la meteorología original. La retícula es una referencia geométrica, no una parcela ni una nueva predicción por subcelda.
- **11 opciones de bosque** más oculto: vista general, pi roig, pi negre, pi blanc, alzinars, suredes, fagedes, rouredes de roure pènol/de fulla gran, avetoses, castanyedes y ribera. Son las capas oficiales de MITECO; no representan todas las formaciones existentes.
- **pH visible u oculto**, fijado en 0–5 cm de profundidad (SoilGrids, resolución nominal de 250 m).
- **15 días anteriores + 7 días de previsión**. La fecha inicial es el primer día de previsión. El histórico se etiqueta por separado y muestra estimaciones retrospectivas, no avistamientos de setas ni predicciones archivadas que se emitieran entonces.
- **24 fotos locales**, una por especie, con fuente, autor y licencia; ver PHOTO_CREDITS.md.
- Aviso visible de desarrollo y orientación, y texto ampliado de uso y seguridad. No sirve para identificar setas, garantizar su presencia ni confirmar comestibilidad. El aviso no garantiza protección jurídica absoluta ni sustituye una revisión legal para el uso concreto.

## Rendimiento

Las capas se conservan al ocultarlas; mostrar de nuevo una misma capa no reinicia su fuente. Se limita el zoom de solicitud de teselas para no pedir detalle inútil al servidor. Solo se consulta el punto de la capa ambiental activa (una petición, sin los dos percentiles adicionales de pH). Los resultados válidos se reutilizan durante diez minutos, con un máximo de 200 puntos en memoria. Los fallos no se guardan. Seleccionar bosque o pH ya no descarga índices de especies innecesariamente.

Los datos regionales publicados se comprimen con gzip y el navegador los descomprime; solo se descarga la región activa y la especie seleccionada. Las fotos están incluidas en el sitio, sin consultas a Wikimedia durante el uso. La retícula se dibuja solo para la vista cercana actual.

La primera carga de MITECO/SoilGrids sigue dependiendo del proveedor y de la conexión. No se ha medido una mejora porcentual ni se garantiza un tiempo de respuesta. Un salto adicional requeriría un servicio propio de teselas precalculadas y caché, con infraestructura fuera del sitio estático.

## Meteorología e interpretación

Se descargan **43 días previos**: 28 para completar los antecedentes de la primera fecha histórica y 15 para mostrar. Cada fecha usa su ventana antecedente de lluvia (según especie, hasta 25 días), temperatura y heladas. La lluvia del propio día queda fuera de su acumulado antecedente; los días futuros incorporan previsiones anteriores de la misma serie. El índice meteorológico y estacional de 0–100 no es una probabilidad y no está calibrado con trabajo de campo. Bosque y pH se consultan independientemente y aún no ponderan ese índice.

Open-Meteo aporta meteorología modelizada, no medidas locales. El muestreo de descarga sigue siendo 0,16° y la interpolación usa cuatro vecinos; las celdas de 1 km no equivalen a observaciones de 1 km. Fechas en Europe/Madrid, incluidas Canarias. Los límites administrativos son generalizados (GISCO 1:1M). El pH estimado no es una medida local y las respuestas vacías se mantienen como desconocidas.

## Ejecutar y probar

Python 3.12+, las dependencias de requirements.txt y conexión para descargar meteorología y usar mapas. Node se usa para las pruebas.

```sh
pip install -r requirements.txt
python src/download_meteo.py --grid-step 0.16 --forecast-days 7
python src/predict_engine.py --cell-km 1 --all-spain
python src/validate_output.py --all-spain
python src/package_site.py
python -m http.server 8000 --bind 127.0.0.1 --directory dist
```

Usa un navegador moderno con DecompressionStream (Chrome, Edge, Firefox o Safari actualizados). Para desarrollo también se puede servir web con sus datos sin comprimir. No abrir index.html mediante file://.

```sh
python -m unittest discover -s tests -v
node --test tests/*.test.cjs
node --check web/app.js
node --check web/environment-layers.js
node --check web/visual-grid.js
```

## Subir a GitHub

Extrae el ZIP y reemplaza los archivos en la raíz de tu repositorio, incluyendo **.github** y **web/images**. No subas el ZIP como sustituto del código. GitHub Pages debe usar GitHub Actions. El workflow conserva el cálculo de 1 km, regenera los 22 días, valida y comprime antes de desplegar. No publiques web/data ni dist en el repositorio. Las actualizaciones fallidas no sustituyen la web publicada. Consulta GITHUB_SETUP.md.

## Fuentes

- [OpenStreetMap](https://www.openstreetmap.org/copyright), © colaboradores.
- [MITECO](https://www.miteco.gob.es/es/biodiversidad/temas/inventarios-nacionales/mapa-forestal-espana.html), Mapa Forestal de España.
- [ISRIC SoilGrids](https://soilgrids.org), CC BY 4.0.
- [Open-Meteo](https://open-meteo.com/en/docs), CC BY 4.0; el servicio público tiene condiciones y límites de uso.
- ICGC: capas opcionales de coberturas del suelo en Cataluña.
- Eurostat GISCO / © EuroGeographics: límites administrativos.
- Wikimedia Commons: fotografías y licencias individuales en PHOTO_CREDITS.md.
- [Canal Salut](https://canalsalut.gencat.cat/ca/salut-a-z/i/intoxicacio-bolets/): información de seguridad enlazada desde el aviso.
