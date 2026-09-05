# Despliegue del CRM en Render

## Recursos creados

El archivo `render.yaml` crea en Frankfurt:

- un servicio web Docker de pago conectado a la rama `deploy`;
- una base de datos PostgreSQL 17 de pago, sin acceso público;
- un disco persistente de 1 GB para datos privados y futuras imágenes.

Los archivos estáticos se compilan dentro de la imagen Docker y se sirven con WhiteNoise. El disco persistente se monta en `/app/data`; las imágenes se guardan en `/app/data/media` y las copias manuales en `/app/data/backups`.

Render despliega automáticamente una revisión de `deploy` únicamente cuando las comprobaciones de GitHub han terminado correctamente.

## Primer despliegue desde Windows

1. Crear una cuenta en Render y activar la autenticación en dos pasos.
2. Abrir **New > Blueprint** en el panel de Render.
3. Conectar GitHub y seleccionar `Pablomv8/inmobiliaria-crm`.
4. Seleccionar la rama `deploy` y el archivo `render.yaml`.
5. Revisar el coste de los tres recursos y pulsar **Apply**.
6. Esperar a que la base de datos y el servicio web aparezcan como disponibles.
7. Abrir la URL `https://inmobiliaria-crm.onrender.com` que indique Render.

No se debe elegir el plan gratuito: no admite el disco persistente y la base de datos gratuita caduca.

## Crear el primer administrador

En la página del servicio web, abrir **Shell** y ejecutar:

```bash
python manage.py createsuperuser
```

Después, comprobar el acceso, el dashboard y las dos rutas de salud:

```text
/health/live/
/health/ready/
```

## Datos temporales para una presentación

Para preparar una base de demostración completa, abrir **Shell** en el servicio web
y ejecutar:

```bash
python manage.py seed_showcase
```

El comando genera y muestra dos contraseñas aleatorias: una para el superusuario y
otra para el manager y los agentes. Hay que guardarlas al ejecutar el comando,
porque Django no permite consultarlas posteriormente. Las cuentas principales son:

```text
admin_demo  Superusuario
pablo       Manager
carlos      Agente
marta       Agente
```

También se crean dos agentes auxiliares para mostrar el flujo integral, datos
geolocalizados de Arcos, contactos, noticias, encargos, pedidos, agenda, tareas,
objetivos, propuestas, ventas y alquileres. Ejecutarlo de nuevo actualiza la misma
demostración sin duplicarla.

Opcionalmente se pueden fijar las contraseñas mediante las variables de entorno
`DEMO_SEED_PASSWORD` y `DEMO_ADMIN_PASSWORD`. Deben ser distintas y contener al
menos 12 caracteres. No se deben incluir sus valores en el repositorio.

Al terminar la presentación, se pueden retirar únicamente los datos reconocibles
de la demostración con:

```bash
python manage.py seed_showcase --purge
```

El comando antiguo `python manage.py seed` no debe utilizarse en producción porque
elimina registros existentes y usa credenciales predecibles.

## Importar las calles de Arcos sin conexión externa

La imagen incluye una instantánea validada del catálogo de calles para evitar que
un fallo de conexión entre Render y Overpass bloquee la carga inicial. Desde
**Shell** se ejecuta:

```bash
python manage.py import_arcos_streets --file tasks/data/arcos_streets.json
```

El comando crea las calles que falten y actualiza las existentes sin duplicarlas.
La opción `--prune` debe reservarse para una sincronización deliberada, ya que
también elimina del catálogo las calles ausentes en la instantánea.

## Dominio del cliente

Cuando se conozca el dominio definitivo:

1. Añadirlo en **Settings > Custom Domains** del servicio.
2. Crear el registro DNS que muestre Render.
3. Añadir o actualizar estas variables del servicio:

```env
DJANGO_ALLOWED_HOSTS=inmobiliaria-crm.onrender.com,crm.dominio-del-cliente.es
DJANGO_CSRF_TRUSTED_ORIGINS=https://inmobiliaria-crm.onrender.com,https://crm.dominio-del-cliente.es
```

4. Volver a desplegar y verificar el inicio de sesión desde el dominio nuevo.

Render añade automáticamente el dominio temporal real a ambas listas. Las variables anteriores son necesarias para el dominio personalizado.

## Operación

- Antes de integrar cambios en `deploy`, ejecutar todas las pruebas.
- Revisar el resultado de GitHub Actions antes de desplegar.
- Consultar los logs y `/health/ready/` después de cada actualización.
- Crear el dominio, la cuenta de Render y la facturación a nombre del cliente o de la empresa responsable.
- Configurar `SENTRY_DSN` posteriormente si se desea recibir alertas de errores.
