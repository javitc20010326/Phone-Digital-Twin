package local.codex.redmisensors;

import android.app.Activity;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONArray;
import org.json.JSONObject;

public class MainActivity extends Activity implements SensorEventListener {
    private SensorManager sensorManager;
    private Sensor orientationSensor;
    private Sensor accelerationSensor;
    private EditText endpointInput;
    private TextView statusText;
    private TextView valuesText;
    private Button startButton;
    private final ExecutorService networkExecutor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private boolean streaming = false;
    private long lastSentMillis = 0L;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
        buildUi();
        chooseSensors();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(36, 42, 36, 36);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        setContentView(root);

        TextView title = new TextView(this);
        title.setText("Redmi Sensor Sender");
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER);
        root.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView help = new TextView(this);
        help.setText("Envia Rotation Vector al gemelo digital del PC. Con USB/ADB reverse usa localhost. Por Wi-Fi usa la IP del PC.");
        help.setTextSize(15);
        help.setPadding(0, 24, 0, 24);
        root.addView(help);

        endpointInput = new EditText(this);
        endpointInput.setSingleLine(true);
        endpointInput.setText("http://127.0.0.1:8876/sensor");
        endpointInput.setSelectAllOnFocus(false);
        root.addView(endpointInput, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        startButton = new Button(this);
        startButton.setText("Iniciar envio");
        startButton.setOnClickListener(view -> toggleStreaming());
        root.addView(startButton, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        statusText = new TextView(this);
        statusText.setText("Preparando sensores...");
        statusText.setTextSize(15);
        statusText.setPadding(0, 28, 0, 16);
        root.addView(statusText);

        valuesText = new TextView(this);
        valuesText.setText("--");
        valuesText.setTextSize(14);
        root.addView(valuesText);
    }

    private void chooseSensors() {
        orientationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
        if (orientationSensor == null) {
            orientationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR);
        }
        accelerationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION);
        if (accelerationSensor == null) {
            accelerationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        }

        if (orientationSensor == null) {
            statusText.setText("No hay Rotation Vector ni Game Rotation Vector.");
            startButton.setEnabled(false);
            return;
        }
        String accelName = accelerationSensor == null ? "sin aceleracion" : accelerationSensor.getName();
        statusText.setText("Sensores: " + orientationSensor.getName() + " + " + accelName);
    }

    private void toggleStreaming() {
        if (streaming) {
            streaming = false;
            sensorManager.unregisterListener(this);
            startButton.setText("Iniciar envio");
            statusText.setText("Parado.");
            return;
        }

        if (orientationSensor == null) {
            chooseSensors();
            if (orientationSensor == null) {
                return;
            }
        }

        streaming = true;
        sensorManager.registerListener(this, orientationSensor, SensorManager.SENSOR_DELAY_GAME);
        if (accelerationSensor != null) {
            sensorManager.registerListener(this, accelerationSensor, SensorManager.SENSOR_DELAY_GAME);
        }
        startButton.setText("Parar");
        statusText.setText("Enviando a " + endpointInput.getText().toString());
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (!streaming) {
            return;
        }

        long now = System.currentTimeMillis();
        if (now - lastSentMillis < 25) {
            return;
        }
        lastSentMillis = now;

        float[] values = event.values.clone();
        if (event.sensor.getType() == Sensor.TYPE_ROTATION_VECTOR ||
                event.sensor.getType() == Sensor.TYPE_GAME_ROTATION_VECTOR) {
            valuesText.setText(String.format(Locale.US, "rot x=%.4f y=%.4f z=%.4f%s",
                    values[0],
                    values.length > 1 ? values[1] : 0f,
                    values.length > 2 ? values[2] : 0f,
                    values.length > 3 ? String.format(Locale.US, " w=%.4f", values[3]) : ""));
            sendSensorValues(event.sensor.getStringType(), values, event.timestamp);
        } else if (event.sensor.getType() == Sensor.TYPE_LINEAR_ACCELERATION ||
                event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            valuesText.setText(String.format(Locale.US, "acc x=%.3f y=%.3f z=%.3f", values[0], values[1], values[2]));
            sendMotion(values, event.timestamp);
        }
    }

    private void sendSensorValues(String sensorType, float[] values, long timestamp) {
        String endpoint = endpointInput.getText().toString().trim();
        networkExecutor.execute(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("type", sensorType);
                body.put("timestamp", timestamp);
                JSONArray array = new JSONArray();
                for (float value : values) {
                    array.put(value);
                }
                body.put("values", array);

                byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
                HttpURLConnection connection = (HttpURLConnection) new URL(endpoint).openConnection();
                connection.setConnectTimeout(700);
                connection.setReadTimeout(700);
                connection.setRequestMethod("POST");
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json");
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(bytes);
                }
                int status = connection.getResponseCode();
                connection.disconnect();
                if (status < 200 || status >= 300) {
                    updateStatus("HTTP " + status);
                }
            } catch (Exception error) {
                updateStatus("Error envio: " + error.getMessage());
            }
        });
    }

    private void sendMotion(float[] values, long timestamp) {
        String endpoint = endpointInput.getText().toString().trim();
        networkExecutor.execute(() -> {
            try {
                JSONObject acceleration = new JSONObject();
                acceleration.put("x", values.length > 0 ? values[0] : 0f);
                acceleration.put("y", values.length > 1 ? values[1] : 0f);
                acceleration.put("z", values.length > 2 ? values[2] : 0f);

                JSONObject body = new JSONObject();
                body.put("type", "devicemotion");
                body.put("timestamp", timestamp);
                body.put("acceleration", acceleration);
                body.put("accelerationIncludingGravity", acceleration);
                body.put("interval", 20);

                byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
                HttpURLConnection connection = (HttpURLConnection) new URL(endpoint).openConnection();
                connection.setConnectTimeout(700);
                connection.setReadTimeout(700);
                connection.setRequestMethod("POST");
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json");
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(bytes);
                }
                int status = connection.getResponseCode();
                connection.disconnect();
                if (status < 200 || status >= 300) {
                    updateStatus("HTTP " + status);
                }
            } catch (Exception error) {
                updateStatus("Error envio: " + error.getMessage());
            }
        });
    }

    private void updateStatus(String message) {
        mainHandler.post(() -> statusText.setText(message));
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (streaming) {
            sensorManager.unregisterListener(this);
            streaming = false;
            startButton.setText("Iniciar envio");
        }
    }
}
