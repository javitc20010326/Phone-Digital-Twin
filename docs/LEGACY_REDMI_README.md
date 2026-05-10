# Redmi Note 13 Pro - gemelo digital local

Este prototipo abre una ventana local en el PC con un modelo 3D procedimental del Redmi Note 13 Pro. La LAN se usa solo para recibir sensores del movil.

## Ejecutar

Haz doble click en `run_redmi_twin.bat`, o ejecuta:

```powershell
& "C:\Users\javit\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" redmi_desktop_twin.py
```

## Opcion A: navegador del movil

Con el PC y el movil en el mismo Wi-Fi, abre en el movil la URL que aparece abajo en la ventana. Suele ser:

```text
http://192.168.1.193:8876/phone
```

Pulsa `Iniciar sensores`.

## Opcion A2: USB + ADB reverse

Si Chrome bloquea sensores por HTTP LAN, usa USB para que el movil abra la pagina como `localhost`.

Guia: `RUTA_RECOMENDADA_USB.md`.

## Opcion B: app Android por UDP

Si el navegador no entrega sensores, instala una app que emita sensores por UDP, por ejemplo SensaGram, HyperIMU o Sensorstream IMU+GPS.

Configura:

- IP destino: la IP del PC que aparece en la ventana.
- Puerto destino: `5005`.
- Sensor preferido: `Rotation Vector`.
- Alternativa: `Orientation`, `Accelerometer` + `Magnetic Field`.
- Formato: JSON si la app lo permite.

Mas detalle: `ANDROID_SENSOR_SOLUTIONS.md`.

## Controles PC

- Arrastrar con el raton: orbitar camara.
- Rueda: zoom.
- `C`: calibrar la posicion actual como cero.
- `R`: reset de calibracion.
- `Espacio`: activar/desactivar control por sensores.
