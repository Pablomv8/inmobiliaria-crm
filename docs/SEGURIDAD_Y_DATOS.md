# Seguridad, archivos y protección de datos

## Configuración

- Nunca confirmar `.env`, copias, base de datos o archivos multimedia en Git.
- Cambiar inmediatamente cualquier secreto que aparezca en un mensaje o repositorio.
- Mantener `DEBUG=False`, HTTPS obligatorio, HSTS y cookies seguras en producción.
- Manager y administrador deben utilizar cuentas personales; no compartir usuarios.
- Revisar periódicamente usuarios inactivos y reasignar su cartera antes de desactivarlos.

## Archivos

Las imágenes de inmuebles:

- Admiten exclusivamente JPEG, PNG o WEBP reales.
- Tienen límite de 8 MB y 40 megapíxeles.
- Se guardan con un nombre aleatorio.
- No se publican mediante `/media/` ni mediante Nginx.
- Se entregan desde una vista autenticada con cabeceras privadas y `nosniff`.

Los futuros DNI, notas simples y contratos deberán utilizar el mismo patrón, con autorización por expediente, descarga forzada y almacenamiento privado. No deben colocarse bajo `/static/`.

## Protección de datos

- Recoger solo información necesaria para la operación inmobiliaria.
- Documentar la base jurídica y el plazo de conservación de cada categoría.
- No incluir DNI, teléfonos, correos, notas ni contratos en logs o Sentry.
- Las exportaciones y copias deben cifrarse cuando salgan del servidor.
- Una solicitud de acceso, rectificación o supresión debe revisarse antes de borrar: ventas, alquileres y correcciones conservan trazabilidad legal.
- Para pruebas y soporte se deben anonimizar nombres, documentos, teléfonos y direcciones reales.

## Respuesta ante incidentes

1. Desactivar el acceso afectado y conservar logs.
2. Rotar secretos y credenciales comprometidos.
3. Identificar registros, usuarios y periodo afectados mediante `request_id` y actividades.
4. Restaurar solo después de verificar una copia.
5. Documentar el incidente y valorar las obligaciones de notificación aplicables.
