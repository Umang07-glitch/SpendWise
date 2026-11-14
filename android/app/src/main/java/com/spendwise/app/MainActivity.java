package com.spendwise.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.app.DownloadManager;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int FILE_PICKER = 10;
    private SharedPreferences preferences;
    private LinearLayout root, body;
    private ProgressBar progress;
    private TextView status;
    private WebView web;
    private String server;
    private ValueCallback<Uri[]> fileCallback;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        preferences = getSharedPreferences("spendwise", MODE_PRIVATE);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(246,248,250));
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout() | WindowInsets.Type.ime());
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            } else {
                view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(), insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            }
            return insets;
        });
        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setGravity(android.view.Gravity.CENTER_VERTICAL);
        toolbar.setPadding(dp(16),dp(6),dp(8),dp(6));
        toolbar.setBackgroundColor(Color.rgb(16,31,50));
        TextView logo = new TextView(this);
        logo.setText("spendwise"); logo.setTextSize(20); logo.setTextColor(Color.WHITE);
        logo.setTypeface(null, android.graphics.Typeface.BOLD);
        toolbar.addView(logo, new LinearLayout.LayoutParams(0,dp(44),1));
        Button reload = new Button(this); reload.setText("Reload");
        reload.setOnClickListener(v -> { if(web != null) web.reload(); });
        toolbar.addView(reload);
        Button settings = new Button(this); settings.setText("Server");
        settings.setOnClickListener(v -> showSetup()); toolbar.addView(settings);
        root.addView(toolbar);
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100); progress.setVisibility(View.GONE);
        root.addView(progress, new LinearLayout.LayoutParams(-1,dp(3)));
        status = new TextView(this); status.setPadding(dp(12),dp(8),dp(12),dp(8));
        status.setTextColor(Color.rgb(130,50,30)); status.setVisibility(View.GONE);
        root.addView(status);
        body = new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL);
        root.addView(body, new LinearLayout.LayoutParams(-1,0,1));
        setContentView(root);
        String saved = preferences.getString("server", "");
        if(saved.isEmpty()) showSetup(); else connect(saved);
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private void destroyWeb() {
        if(fileCallback != null) { fileCallback.onReceiveValue(null); fileCallback = null; }
        if(web != null) { web.stopLoading(); web.destroy(); web = null; }
        body.removeAllViews();
    }

    private void showSetup() {
        destroyWeb(); status.setVisibility(View.GONE); progress.setVisibility(View.GONE);
        LinearLayout form = new LinearLayout(this); form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(dp(24),dp(36),dp(24),dp(24));
        TextView heading = new TextView(this); heading.setText("Your finances, on your phone.");
        heading.setTextSize(26); heading.setTextColor(Color.rgb(16,31,50));
        heading.setTypeface(null, android.graphics.Typeface.BOLD); form.addView(heading);
        TextView description = new TextView(this);
        description.setText("Enter your SpendWise website address. For a college demo, connect this phone and your laptop to the same Wi-Fi and keep both servers running. Use the laptop's Wi-Fi IPv4 address, not localhost.\n\nExample: http://192.168.1.20:3000\nAndroid emulator: http://10.0.2.2:3000\n\nLocal HTTP is intended only for fictional development data. A deployed service should use HTTPS.");
        description.setTextSize(14); description.setLineSpacing(dp(4),1);
        description.setPadding(0,dp(18),0,dp(24)); form.addView(description);
        TextView label = new TextView(this); label.setText("SpendWise server address"); form.addView(label);
        EditText address = new EditText(this); address.setSingleLine(true);
        address.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        address.setHint("http://192.168.1.20:3000");
        address.setText(preferences.getString("server", "")); form.addView(address);
        label.setLabelFor(address.getId() == View.NO_ID ? (address.getId()) : address.getId());
        Button connect = new Button(this); connect.setText("Connect to SpendWise");
        connect.setOnClickListener(v -> {
            try {
                boolean debug = (getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0;
                String url = ServerAddress.normalize(address.getText().toString(), debug);
                String previous = preferences.getString("server", "");
                if (!previous.isEmpty() && !previous.equals(url)) {
                    new AlertDialog.Builder(this).setTitle("Change server?")
                        .setMessage("Only connect to a server you trust. Your login cookies will be cleared before switching.")
                        .setNegativeButton("Cancel",null)
                        .setPositiveButton("Connect", (dialog, which) -> CookieManager.getInstance().removeAllCookies(done -> connect(url))).show();
                } else connect(url);
            } catch(IllegalArgumentException ex) { address.setError(ex.getMessage()); }
        });
        form.addView(connect);
        android.widget.ScrollView scroll = new android.widget.ScrollView(this); scroll.addView(form);
        body.addView(scroll, new LinearLayout.LayoutParams(-1,-1));
    }

    private void connect(String url) {
        try {
            boolean debug = (getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0;
            server = ServerAddress.normalize(url, debug);
        } catch(IllegalArgumentException e) { showSetup(); return; }
        preferences.edit().putString("server", server).apply();
        destroyWeb(); status.setVisibility(View.GONE);
        web = new WebView(this);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true); settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false); settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false); settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSafeBrowsingEnabled(true); settings.setBuiltInZoomControls(false);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                // Keep credentials and navigation inside the explicitly chosen server.
                if(ServerAddress.sameOrigin(server,request.getUrl().toString())) return false;
                Toast.makeText(MainActivity.this,"External navigation blocked. Open trusted links in your browser.",Toast.LENGTH_LONG).show();
                return true;
            }
            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel(); showError("The server's HTTPS certificate could not be verified. Check the address and certificate.");
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if(request.isForMainFrame()) showError("Cannot reach SpendWise. Check Wi-Fi, the server address, and that your laptop servers are running. Tap Reload to retry or Server to change the address.");
            }
            @Override public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse error) {
                if(request.isForMainFrame() && error.getStatusCode() >= 400) showError("The server returned HTTP " + error.getStatusCode() + ". Check the server address, then tap Reload.");
            }
            @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap icon) { status.setVisibility(View.GONE); }
            @Override public void onPageFinished(WebView view, String url) { CookieManager.getInstance().flush(); }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view,int value) { progress.setProgress(value); progress.setVisibility(value == 100 ? View.GONE : View.VISIBLE); }
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if(fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE); intent.setType("*/*");
                try { startActivityForResult(intent,FILE_PICKER); }
                catch(android.content.ActivityNotFoundException e) { fileCallback.onReceiveValue(null); fileCallback=null; Toast.makeText(MainActivity.this,"No file picker available",Toast.LENGTH_LONG).show(); }
                return true;
            }
        });
        web.setDownloadListener((downloadUrl,userAgent,contentDisposition,mimeType,contentLength) -> {
            if(!ServerAddress.sameOrigin(server,downloadUrl)) { showError("Download blocked: unexpected server."); return; }
            String path = Uri.parse(downloadUrl).getPath();
            if(path == null || !path.startsWith("/api/export/")) { showError("Only SpendWise CSV report downloads are supported."); return; }
            if(Build.VERSION.SDK_INT < 29) { showError("CSV downloads in this app require Android 10 or later. Use your browser on this device."); return; }
            try {
                DownloadManager.Request request = new DownloadManager.Request(Uri.parse(downloadUrl));
                String cookie = CookieManager.getInstance().getCookie(downloadUrl);
                if(cookie != null) request.addRequestHeader("Cookie",cookie);
                request.addRequestHeader("User-Agent",userAgent);
                String filename = path.endsWith("report") ? "spendwise-report-" : "spendwise-transactions-";
                request.setTitle("SpendWise CSV export"); request.setMimeType("text/csv");
                request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,filename+System.currentTimeMillis()+".csv");
                ((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(request);
                Toast.makeText(MainActivity.this,"CSV download started. Check Downloads for completion.",Toast.LENGTH_LONG).show();
            } catch(Exception ex) { showError("Could not start the download. Check your device's download manager."); }
        });
        body.addView(web, new LinearLayout.LayoutParams(-1,-1)); web.loadUrl(server);
    }

    private void showError(String message) { status.setText(message); status.setVisibility(View.VISIBLE); }

    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data) {
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode == FILE_PICKER && fileCallback != null) {
            Uri uri = resultCode == RESULT_OK && data != null ? data.getData() : null;
            fileCallback.onReceiveValue(uri == null ? null : new Uri[]{uri}); fileCallback=null;
        }
    }
    @Override public void onBackPressed() {
        if(web != null && web.canGoBack()) web.goBack();
        else new AlertDialog.Builder(this).setTitle("Close SpendWise?").setNegativeButton("Stay",null).setPositiveButton("Close",(dialog,which)->finish()).show();
    }
    @Override protected void onPause() { if(web != null) { web.onPause(); CookieManager.getInstance().flush(); } super.onPause(); }
    @Override protected void onResume() { super.onResume(); if(web != null) web.onResume(); }
    @Override protected void onDestroy() { destroyWeb(); super.onDestroy(); }
}
