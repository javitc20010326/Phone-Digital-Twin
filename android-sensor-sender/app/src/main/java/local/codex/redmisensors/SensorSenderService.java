package local.codex.redmisensors;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Build;
import android.os.IBinder;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import org.json.JSONArray;
import org.json.JSONObject;

public class SensorSenderService extends Service implements SensorEventListener {
    public static final String EXTRA_ENDPOINT = "endpoint";

    private static final String CHANNEL_ID = "phone_digital_twin_sender";
    private static final int NOTIFICATION_ID = 42;
    private static final String PREFS = "sensor_sender";
    private static final String KEY_STREAMING = "streaming";

    private SensorManager sensorManager;
    private Sensor orientationSensor;
    private final ExecutorService networkExecutor = Executors.newSingleThreadExecutor();
    private final AtomicBoolean requestInFlight = new AtomicBoolean(false);
    private String endpoint = "udp://192.168.1.193:5005";
    private long lastRotationSentMillis = 0L;
    private long sentPackets = 0L;
    private long droppedPackets = 0L;
    private DatagramSocket udpSocket;
    private String udpEndpointCache = "";
    private InetAddress udpAddress;
    private int udpPort = 5005;

    @Override
    public void onCreate() {
        super.onCreate();
        sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && intent.hasExtra(EXTRA_ENDPOINT)) {
            endpoint = intent.getStringExtra(EXTRA_ENDPOINT);
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_STREAMING, true).apply();
        startForeground(NOTIFICATION_ID, buildNotification("Enviando sensores"));
        startSensors();
        return START_STICKY;
    }

    private void startSensors() {
        if (orientationSensor == null) {
            orientationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
            if (orientationSensor == null) {
                orientationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR);
            }
        }
        if (orientationSensor != null) {
            sensorManager.unregisterListener(this);
            sensorManager.registerListener(this, orientationSensor, SensorManager.SENSOR_DELAY_GAME);
        } else {
            stopSelf();
        }
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (event.sensor.getType() != Sensor.TYPE_ROTATION_VECTOR &&
                event.sensor.getType() != Sensor.TYPE_GAME_ROTATION_VECTOR) {
            return;
        }

        long now = System.currentTimeMillis();
        boolean udpEndpoint = endpoint.toLowerCase(Locale.US).startsWith("udp://");
        long minIntervalMillis = udpEndpoint ? 16L : 33L;
        if (now - lastRotationSentMillis < minIntervalMillis) {
            return;
        }
        lastRotationSentMillis = now;
        sendSensorValues(event.sensor.getStringType(), event.values.clone(), event.timestamp);
    }

    private void sendSensorValues(String sensorType, float[] values, long timestamp) {
        boolean udpEndpoint = endpoint.toLowerCase(Locale.US).startsWith("udp://");
        if (!udpEndpoint && !requestInFlight.compareAndSet(false, true)) {
            droppedPackets++;
            return;
        }
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
                if (udpEndpoint) {
                    sendUdp(bytes);
                    sentPackets++;
                    return;
                }

                HttpURLConnection connection = (HttpURLConnection) new URL(endpoint).openConnection();
                connection.setConnectTimeout(1800);
                connection.setReadTimeout(1800);
                connection.setRequestMethod("POST");
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setRequestProperty("Connection", "keep-alive");
                connection.setFixedLengthStreamingMode(bytes.length);
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(bytes);
                }
                int status = connection.getResponseCode();
                if (status >= 200 && status < 300) {
                    sentPackets++;
                }
            } catch (Exception error) {
                updateNotification("Error envio: " + error.getMessage());
            } finally {
                if (!udpEndpoint) {
                    requestInFlight.set(false);
                }
            }
        });
    }

    private void sendUdp(byte[] bytes) throws Exception {
        if (!endpoint.equals(udpEndpointCache) || udpSocket == null || udpSocket.isClosed()) {
            URI uri = new URI(endpoint);
            String host = uri.getHost();
            if (host == null || host.isEmpty()) {
                throw new IllegalArgumentException("UDP host vacio");
            }
            int port = uri.getPort() > 0 ? uri.getPort() : 5005;
            udpAddress = InetAddress.getByName(host);
            udpPort = port;
            if (udpSocket != null) {
                udpSocket.close();
            }
            udpSocket = new DatagramSocket();
            udpEndpointCache = endpoint;
        }
        udpSocket.send(new DatagramPacket(bytes, bytes.length, udpAddress, udpPort));
    }

    private void updateNotification(String text) {
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.notify(NOTIFICATION_ID, buildNotification(text));
    }

    private Notification buildNotification(String text) {
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        return builder
                .setContentTitle("Phone Digital Twin")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_menu_compass)
                .setOngoing(true)
                .build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Phone Digital Twin",
                    NotificationManager.IMPORTANCE_LOW);
            NotificationManager manager = getSystemService(NotificationManager.class);
            manager.createNotificationChannel(channel);
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_STREAMING, false).apply();
        sensorManager.unregisterListener(this);
        if (udpSocket != null) {
            udpSocket.close();
        }
        networkExecutor.shutdownNow();
        super.onDestroy();
    }
}
