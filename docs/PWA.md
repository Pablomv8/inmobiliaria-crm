# PWA de InmoCRM

La aplicación puede instalarse desde un navegador compatible sin dejar de ser
una aplicación web Django. En Chromium aparece el botón **Instalar** en la barra
superior cuando el navegador confirma que se cumplen los requisitos.

En iPhone o iPad, el botón muestra las instrucciones para usar **Compartir >
Añadir a pantalla de inicio**.

## Estrategia sin conexión

El service worker solo almacena recursos públicos bajo `/static/` y la página
`/offline/`. Las navegaciones del CRM siempre se solicitan al servidor y no se
guardan en caché, por lo que fichas de personas, inmuebles, encargos, pedidos y
formularios autenticados no quedan disponibles sin conexión.

Las operaciones de creación, edición y eliminación necesitan conexión.

## Versionado del caché

En Render se utiliza `RENDER_GIT_COMMIT` como versión del caché. Cada despliegue
crea una versión nueva y elimina las anteriores al activar el service worker.
También se puede establecer `PWA_CACHE_VERSION` manualmente.

## Regenerar iconos

```powershell
.\venv\Scripts\python.exe scripts\generate_pwa_icons.py
```

## Comprobaciones

```powershell
.\venv\Scripts\python.exe manage.py test config.test_pwa
.\venv\Scripts\python.exe manage.py collectstatic --noinput
```
