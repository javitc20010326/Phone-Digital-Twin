<p align="center">
  <img src="docs/phone-digital-twin-hero.svg" alt="Phone Digital Twin" width="100%">
</p>

# Phone Digital Twin

Phone Digital Twin turns an Android phone into a live sensor controller for a local 3D phone model on your PC. The PC renders the digital twin; the phone streams rotation, acceleration and motion data over USB/ADB, Wi-Fi/LAN, or a native Android APK.

The current prototype includes a Xiaomi Redmi Note 13 Pro styled model, but the sensor pipeline works with most Android phones that expose rotation-vector and motion sensors.

## What It Does

- Renders a local 3D phone twin on Windows.
- Mirrors real phone rotation using Android rotation-vector/quaternion data.
- Adds visual XYZ movement from acceleration data.
- Supports USB tunneling with `adb reverse`.
- Includes a native Android sensor sender APK project.
- Includes a browser sensor bridge as a quick fallback.
- Provides scripts and docs so other Codex users can reproduce the setup.

## Quick Start: USB + Native APK

1. Enable Developer Options on Android.
2. Enable:
   - `USB debugging`
   - `Install via USB`
   - `USB debugging (Security settings)` if your Xiaomi/MIUI/HyperOS exposes it
3. Connect the phone by USB and accept the RSA prompt.
4. Start the PC twin:

```powershell
.\run_phone_digital_twin.bat
```

5. Install/open the Android sender:

```powershell
.\scripts\install_apk_usb.ps1
```

6. In the phone app, keep the endpoint as:

```text
http://127.0.0.1:8876/sensor
```

7. Tap `Iniciar envio`.

## Quick Start: USB + Browser Bridge

If you do not want to install the APK:

```powershell
.\scripts\start_usb_browser_bridge.ps1
```

Then tap `Iniciar sensores` in Chrome on the phone.

## PC Controls

- Drag mouse: orbit camera.
- Mouse wheel: zoom.
- `C`: calibrate current orientation.
- `R`: reset calibration.
- `X`: center XYZ movement.
- `M`: toggle XYZ movement.
- `P`: toggle projection mode.
- `Space`: toggle sensor control.

## Accuracy Notes

Rotation can be very good because Android fuses accelerometer, gyroscope and magnetometer into rotation-vector/quaternion sensors.

Absolute XYZ position is a harder problem. A phone accelerometer measures acceleration, not position. Position requires double integration, which drifts. This project uses acceleration-driven visual motion with damping and bounds. For true physical position tracking, the next step is ARCore/camera tracking, visual markers, UWB, or external tracking.

## Project Layout

```text
redmi_desktop_twin.py          PC renderer and sensor receiver
mobile_sensor_bridge.html      Browser fallback sensor bridge
android-sensor-sender/         Native Android APK source
scripts/                       setup, build, install, publish helpers
docs/                          images and manuals
```

## For Codex Users

Use this repository as a starting point for phone-controlled digital twins, sensor visualizers, field-data capture, vibration studies, HMI prototypes, and Android-to-PC engineering workflows.

See:

- [USB + ADB setup](docs/USB_ADB_SETUP.md)
- [Android sensor options](docs/ANDROID_SENSOR_SOLUTIONS.md)
- [USB debugging + Codex ideas](docs/DEPURACION_USB_CODEX.md)
- [Native APK notes](docs/NATIVE_APK.md)

## Publish Your Fork

This repository includes a PowerShell publisher that asks for a GitHub token and uploads the clean source tree:

```powershell
.\scripts\publish_to_github.ps1
```

It excludes local SDKs, Gradle caches, platform-tools downloads and build outputs.
