# Native Android APK

The native APK is the recommended sensor sender when browser APIs are unstable.

It reads Android sensors directly through `SensorManager`:

- `TYPE_ROTATION_VECTOR` or `TYPE_GAME_ROTATION_VECTOR` for orientation.
- `TYPE_LINEAR_ACCELERATION` for XYZ visual movement.
- `TYPE_ACCELEROMETER` fallback when linear acceleration is unavailable.

It posts JSON to the PC receiver:

```text
http://127.0.0.1:8876/sensor
```

With `adb reverse tcp:8876 tcp:8876`, that Android-local endpoint is forwarded to the PC app.

## Build

```powershell
.\scripts\build_apk.ps1
```

The script downloads and prepares a local Android toolchain under `tools/`.

## Install By USB

Enable on the phone:

- Developer options
- USB debugging
- Install via USB
- USB debugging (Security settings), on Xiaomi/MIUI/HyperOS when available

Then run:

```powershell
.\scripts\install_apk_usb.ps1
```

## Use

1. Start the PC twin with `run_phone_digital_twin.bat`.
2. Open the Android app.
3. Endpoint should be `http://127.0.0.1:8876/sensor`.
4. Tap `Iniciar envio`.

## Why Native Helps

Chrome can throttle, mix, or block sensor APIs depending on secure context and browser policy. The native APK reads Android's fused sensors directly, which is better for a digital-twin controller.
