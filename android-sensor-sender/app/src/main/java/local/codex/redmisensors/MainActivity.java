package local.codex.redmisensors;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    private static final String PREFS = "sensor_sender";
    private static final String KEY_ENDPOINT = "endpoint";
    private static final String KEY_STREAMING = "streaming";
    private static final String DEFAULT_ENDPOINT = "udp://192.168.1.193:5005";

    private EditText endpointInput;
    private TextView statusText;
    private Button startButton;
    private boolean streaming = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestNotificationPermission();
        buildUi();
    }

    @Override
    protected void onResume() {
        super.onResume();
        syncStreamingState();
    }

    private void buildUi() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(36, 42, 36, 36);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        setContentView(root);

        TextView title = new TextView(this);
        title.setText("Phone Digital Twin Sender");
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER);
        root.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView help = new TextView(this);
        help.setText("Envia Rotation Vector en segundo plano. Para maxima suavidad en LAN usa udp://IP_DEL_PC:5005. Se detiene solo al pulsar Parar envio.");
        help.setTextSize(15);
        help.setPadding(0, 24, 0, 24);
        root.addView(help);

        endpointInput = new EditText(this);
        endpointInput.setSingleLine(true);
        endpointInput.setText(prefs.getString(KEY_ENDPOINT, DEFAULT_ENDPOINT));
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
        statusText.setText("Listo. Pulsa iniciar y puedes salir de la APK.");
        statusText.setTextSize(15);
        statusText.setPadding(0, 28, 0, 16);
        root.addView(statusText);
    }

    private void toggleStreaming() {
        syncStreamingState();
        if (streaming) {
            stopService(new Intent(this, SensorSenderService.class));
            streaming = false;
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_STREAMING, false).apply();
            startButton.setText("Iniciar envio");
            statusText.setText("Envio detenido.");
            return;
        }

        String endpoint = endpointInput.getText().toString().trim();
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_ENDPOINT, endpoint).apply();

        Intent intent = new Intent(this, SensorSenderService.class);
        intent.putExtra(SensorSenderService.EXTRA_ENDPOINT, endpoint);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent);
        } else {
            startService(intent);
        }
        streaming = true;
        startButton.setText("Parar envio");
        statusText.setText("Enviando en segundo plano a " + endpoint);
    }

    private void syncStreamingState() {
        streaming = getSharedPreferences(PREFS, MODE_PRIVATE).getBoolean(KEY_STREAMING, false);
        if (startButton != null) {
            startButton.setText(streaming ? "Parar envio" : "Iniciar envio");
        }
        if (statusText != null && streaming) {
            statusText.setText("Servicio activo en segundo plano.");
        }
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 10);
        }
    }
}
