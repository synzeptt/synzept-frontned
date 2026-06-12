package com.synzept.app;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;

public class MainActivity extends Activity {
    private static final String CHROME_PACKAGE = "com.android.chrome";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.WHITE);
        getWindow().setNavigationBarColor(Color.WHITE);
        openSynzeptInSupportedBrowser();
        finish();
    }

    private void openSynzeptInSupportedBrowser() {
        Uri appUri = Uri.parse(BuildConfig.SYNZEPT_URL);
        Intent chromeIntent = new Intent(Intent.ACTION_VIEW, appUri);
        chromeIntent.setPackage(CHROME_PACKAGE);
        chromeIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        try {
            startActivity(chromeIntent);
        } catch (ActivityNotFoundException chromeMissing) {
            Intent browserIntent = new Intent(Intent.ACTION_VIEW, appUri);
            browserIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(browserIntent);
        }
    }
}
