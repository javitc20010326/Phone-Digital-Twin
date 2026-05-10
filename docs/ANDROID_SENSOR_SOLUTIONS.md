# Soluciones para sensores Android -> PC

El modelo 3D se ejecuta en el PC. El movil solo debe enviar sensores.

## Opcion 1: Chrome Android marcando el origen como seguro

Esto mantiene la pagina movil, pero desbloquea APIs que Chrome oculta en HTTP.

1. En el Xiaomi abre Chrome.
2. En la barra escribe:

```text
chrome://flags/#unsafely-treat-insecure-origin-as-secure
```

3. Activa la flag.
4. En el campo de origen escribe exactamente:

```text
http://192.168.1.193:8876
```

5. Pulsa `Relaunch`.
6. Vuelve a abrir:

```text
http://192.168.1.193:8876/phone
```

7. Pulsa `Iniciar sensores`.

Si Chrome Android no conserva la flag tras reiniciar, usa la opcion UDP.

## Opcion 2: SensaGram por UDP

Esta es la via no-web recomendada.

1. Instala SensaGram en Android.
2. IP destino:

```text
192.168.1.193
```

3. Puerto:

```text
5005
```

4. Selecciona `Rotation Vector`. Si no aparece, selecciona `Game Rotation Vector`.
5. Formato: JSON.
6. Pulsa `Stream`.

La app del PC acepta paquetes tipo:

```json
{"type":"android.sensor.rotation_vector","values":[0,0,0,1]}
```

Tambien acepta acelerometro + magnetometro como fallback, pero `Rotation Vector` es mejor porque Android ya fusiona acelerometro, giroscopio y brujula.

## Opcion 3: HyperIMU por UDP

1. Instala HyperIMU.
2. Elige streaming por `UDP`.
3. Host/IP: `192.168.1.193`.
4. Puerto: `5005`.
5. Formato: `JSON` si esta disponible.
6. Sensor preferido: `Rotation Vector` o `Game Rotation Vector`.
7. Frecuencia: 30 Hz o 50 Hz.

## Opcion 4: HTTPS real

Para que Chrome Android trate la pagina como segura sin flags hay que usar HTTPS con certificado confiable para el movil. Un certificado autofirmado normal no basta si Chrome lo sigue marcando como no confiable.

Ruta correcta:

1. Crear una CA local.
2. Crear certificado para `192.168.1.193` con Subject Alternative Name.
3. Instalar la CA en Android como certificado de usuario.
4. Servir la pagina en HTTPS desde el PC.

Esto es mas largo y frágil que UDP, pero se puede hacer si quieres mantener navegador.
