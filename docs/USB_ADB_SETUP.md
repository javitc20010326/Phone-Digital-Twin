# Ruta recomendada: USB + ADB reverse

Esta es la mejor ruta antes de hacer una APK propia:

- No necesita dominio.
- No necesita HTTPS real.
- No depende de que el movil vea la IP LAN del PC.
- Chrome Android abre `http://localhost:8876/phone`, que suele tratarse como origen local seguro.
- La app 3D sigue ejecutandose local en el PC.

## Paso 1: instalar ADB minimo

Descarga Android SDK Platform-Tools oficial:

```text
https://developer.android.com/tools/releases/platform-tools
```

Extrae el ZIP dentro de esta carpeta del proyecto, para que quede asi:

```text
C:\Users\javit\Documents\Codex\2026-05-10\quiero-hacer-un-sistema-proyecto-y\platform-tools\adb.exe
```

No necesitas Android Studio para este paso.

## Paso 2: activar opciones de desarrollador en Xiaomi

1. Ajustes.
2. Sobre el telefono.
3. Pulsa 7 veces en `Version de MIUI` o `Version del SO`.
4. Vuelve a Ajustes.
5. Ajustes adicionales.
6. Opciones de desarrollador.
7. Activa `Depuracion USB`.

En Xiaomi/HyperOS/MIUI puede aparecer tambien:

- `Instalar via USB`
- `Depuracion USB (Ajustes de seguridad)`

Para ADB reverse normalmente basta `Depuracion USB`.

## Paso 3: conectar USB

1. Conecta el movil al PC con cable USB de datos.
2. En el movil acepta la ventana de huella RSA.
3. Marca `Permitir siempre desde este ordenador` si aparece.

## Paso 4: arrancar app PC

Ejecuta:

```text
run_redmi_twin.bat
```

## Paso 5: crear tunel USB

Ejecuta:

```text
usb_adb_reverse.bat
```

El script hara:

```text
adb reverse tcp:8876 tcp:8876
adb shell am start -a android.intent.action.VIEW -d http://localhost:8876/phone
```

## Paso 6: probar sensores

En el movil pulsa:

```text
Iniciar sensores
```

Si funciona, en el PC debe cambiar a `recibiendo sensores`.

## Si falla

Ejecuta `usb_adb_reverse.bat` y dime exactamente que aparece en:

```text
Dispositivos detectados:
```

Estados posibles:

- `device`: correcto.
- `unauthorized`: mira el movil y acepta la huella RSA.
- vacio: cable incorrecto, drivers o depuracion USB no activa.
- `offline`: desconecta/conecta USB y acepta de nuevo.
