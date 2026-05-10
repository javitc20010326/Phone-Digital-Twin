# Depuracion USB + Codex: alcance practico

## Que es

La depuracion USB permite que el PC hable con Android mediante ADB. Con tu autorizacion RSA, el PC puede instalar apps de desarrollo, abrir actividades, leer logs, reenviar puertos, copiar archivos y ejecutar comandos de diagnostico.

## Opciones Xiaomi utiles

- `Depuracion USB`: conexion ADB basica.
- `Instalar via USB`: permite `adb install` de APKs propias.
- `Depuracion USB (ajustes de seguridad)`: permite acciones mas potentes, como simular taps o cambiar permisos/ajustes desde ADB. Xiaomi suele bloquear algunas acciones sin esto.
- `Verificar apps por USB`: puede bloquear APKs debug. Si molesta, desactivarlo temporalmente durante pruebas.

## Para este proyecto

- `adb reverse tcp:8876 tcp:8876`: el movil abre `http://localhost:8876`, pero realmente habla con la app del PC.
- `adb install -r app-debug.apk`: instala la APK nativa de sensores.
- `adb shell am start ...`: abre la web local o la app.
- `adb logcat`: permite ver errores de la APK en tiempo real.

## Ejemplos utiles

Ver movil conectado:

```powershell
.\platform-tools\adb.exe devices -l
```

Crear tunel USB:

```powershell
.\platform-tools\adb.exe reverse tcp:8876 tcp:8876
```

Ver tuneles activos:

```powershell
.\platform-tools\adb.exe reverse --list
```

Instalar APK:

```powershell
.\platform-tools\adb.exe install -r android-sensor-sender\app\build\outputs\apk\debug\app-debug.apk
```

Abrir la APK:

```powershell
.\platform-tools\adb.exe shell monkey -p local.codex.redmisensors 1
```

Leer logs de la APK:

```powershell
.\platform-tools\adb.exe logcat | Select-String redmisensors
```

Copiar archivo al movil:

```powershell
.\platform-tools\adb.exe push archivo.txt /sdcard/Download/
```

Copiar archivo desde el movil:

```powershell
.\platform-tools\adb.exe pull /sdcard/Download/archivo.txt .
```

Captura de pantalla:

```powershell
.\platform-tools\adb.exe exec-out screencap -p > pantalla.png
```

Grabar pantalla:

```powershell
.\platform-tools\adb.exe shell screenrecord /sdcard/Download/demo.mp4
```

Ver sensores disponibles:

```powershell
.\platform-tools\adb.exe shell dumpsys sensorservice
```

Ver bateria/temperatura:

```powershell
.\platform-tools\adb.exe shell dumpsys battery
```

Ver Wi-Fi/IP:

```powershell
.\platform-tools\adb.exe shell ip addr
```

## Como Codex lo puede potenciar

- Compilar APKs y probarlas en tu movil.
- Instalar versiones nuevas automaticamente.
- Leer logs y corregir bugs.
- Crear tuneles USB para comunicar movil-PC sin configurar red.
- Capturar pantallas y analizar UI.
- Crear scripts de automatizacion para pruebas.
- Leer sensores con app nativa y alimentar simuladores en PC.
- Montar prototipos industriales: HMI movil, gemelo digital, captura de vibraciones, registro de datos, pruebas de campo.

## Limites y seguridad

ADB es potente. No debes aceptar RSA de PCs desconocidos. Cuando acabes, puedes revocar autorizaciones en opciones de desarrollador. Evita ejecutar comandos que borren datos si no entiendes el efecto.
