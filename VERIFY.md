# Verificación de la versión 2

Comprobaciones locales del 5 de noviembre de 2026:

- 14 pruebas Python y 11 pruebas JavaScript superadas.
- Sintaxis comprobada en app.js, environment-layers.js y visual-grid.js.
- Histórico: 15 días anteriores y 7 días de previsión, usando 43 días de antecedentes descargados. La prueba comprueba que la lluvia del propio día no entra en su acumulado antecedente.
- Empaquetado probado: JSON/GeoJSON regionales comprimidos con gzip, manifest sin comprimir y las 24 fotografías incluidas con créditos.
- Chrome real, con meteorología sintética y teselas simuladas: carga gzip, 22 fechas, selección inicial de previsión, las 24 fotos, retícula visual de 250 m, exclusión bosque/pH, fecha histórica y botón móvil. Cero errores JavaScript. Revisadas capturas de escritorio y móvil.
- El servicio GetCapabilities de MITECO respondió HTTP 200 y contiene las 11 capas de bosque usadas.
- Reutilización de consultas de puntos y ausencia de reinicio de teselas al volver a mostrar el pH comprobadas mediante pruebas.

La retícula es visual: el cálculo sigue a 1 km y la meteorología original es más gruesa. No se ha medido un porcentaje de aceleración ni comprobado exhaustivamente la disponibilidad de teselas y puntos de los proveedores. Las fotos proceden de Wikimedia Commons, con atribuciones y licencias en PHOTO_CREDITS.md.

No se ha descargado ni generado en esta revisión la previsión nacional completa de 22 fechas, ni ejecutado GitHub Actions remotamente. El workflow conserva la descarga, generación, validación y compresión antes del despliegue. El ZIP contiene código y fotografías, no meteorología actual lista para abrir sin ejecutar el pipeline. No se ha publicado nada.
