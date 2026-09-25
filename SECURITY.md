# Modelo de seguridad

## Uso autorizado

Retro Audit está diseñado para activos propios o incluidos explícitamente en el alcance de una evaluación autorizada. No realiza explotación, fuerza bruta, enumeración de rutas ni evasión de controles.

## Controles implementados

- La confirmación se vincula al texto actual del objetivo y se revoca al editarlo.
- Los objetivos rechazan caracteres de control, credenciales embebidas, esquemas no admitidos y puertos inválidos.
- Las URLs mostradas e informadas omiten query y fragmento para reducir exposición de secretos.
- HTTP usa una única solicitud `HEAD` y no reintenta respuestas `429`.
- Las redirecciones sólo pueden conservar host y puerto; se bloquea el downgrade de HTTPS a HTTP.
- Las conexiones tienen timeout y el escaneo TCP usa una lista fija de puertos.
- Banner Grabbing consulta una lista fija de servicios, lee como máximo 1 KiB por conexión y sanitiza caracteres de control antes de mostrarlos.
- Los probes activos se limitan a peticiones de identificación mínimas; no autentican, modifican estado ni envían payloads de explotación.
- Los informes usan nombres impredecibles, creación exclusiva y permisos `0600`.
- Los directorios de informes simbólicos son rechazados y `reports/` está ignorado por Git.
- Valores de cookies no se guardan; sólo se evalúan sus atributos defensivos.
- La verificación SSH realiza una sola llamada de conexión, deshabilita agente y búsqueda automática de claves, no reintenta y aplica `RejectPolicy` a hosts desconocidos.
- Los campos secretos se muestran en controles enmascarados, se eliminan del diccionario de trabajo al finalizar y nunca se escriben en actividad, resultado o informe.
- La auditoría de configuración SSH no prueba contraseñas. Sólo consulta métodos mediante autenticación `none` cuando el operador proporciona voluntariamente un usuario.
- La fortaleza de contraseña y la política de bloqueo se procesan exclusivamente en memoria local.
- El detector de fuerza bruta sólo acepta archivos regulares locales no simbólicos de hasta 5 MiB y limita la salida a 50 orígenes.

## Limitaciones conocidas

- La resolución DNS del sistema operativo no ofrece un deadline total estricto.
- La presencia de una cabecera no demuestra que su política sea semánticamente robusta.
- El análisis no sustituye una revisión manual, un escáner autenticado ni una metodología formal como OWASP WSTG.
- Los resultados dependen de la ruta de red y del almacén de certificados local.
- La estimación de entropía de contraseña es teórica y no sustituye un estimador basado en patrones ni una política corporativa.
- Consultar métodos SSH con un usuario puede generar un evento de autenticación `none` en el servidor, aunque no envía ni prueba credenciales.

## Divulgación de resultados

Los informes pueden contener nombres de host, direcciones IP, puertos y configuración defensiva. Deben tratarse como información sensible y no publicarse en repositorios ni adjuntarse sin revisión.
