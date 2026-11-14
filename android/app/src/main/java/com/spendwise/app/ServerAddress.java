package com.spendwise.app;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

/** Shared URL validation; no credentials or URLs outside the chosen origin. */
public final class ServerAddress {
    private ServerAddress() {}

    public static String normalize(String input, boolean allowLocalHttp) {
        try {
            URI uri = new URI(input.trim());
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
            String host = uri.getHost();
            if (host == null || uri.getRawUserInfo() != null || uri.getRawQuery() != null
                    || uri.getRawFragment() != null || (uri.getRawPath() != null
                    && !uri.getRawPath().isEmpty() && !uri.getRawPath().equals("/"))
                    || uri.getPort() < -1 || uri.getPort() == 0 || uri.getPort() > 65535) {
                throw new IllegalArgumentException("Enter only the server origin, for example http://192.168.1.20:3000");
            }
            if (!scheme.equals("https") && !(allowLocalHttp && scheme.equals("http") && isPrivateHost(host))) {
                throw new IllegalArgumentException("Use HTTPS, or a private network HTTP address for this development app.");
            }
            return new URI(scheme, null, host.toLowerCase(Locale.ROOT), uri.getPort(), null, null, null).toASCIIString();
        } catch (URISyntaxException ex) {
            throw new IllegalArgumentException("Enter a valid server URL including http:// or https://");
        }
    }

    private static boolean isPrivateHost(String host) {
        if (host.equalsIgnoreCase("localhost") || host.equals("[::1]") || host.equals("::1")) return true;
        String[] parts = host.split("\\.");
        if (parts.length != 4) return false;
        int[] ip = new int[4];
        try {
            for (int i = 0; i < 4; i++) {
                if (!parts[i].matches("[0-9]{1,3}")) return false;
                ip[i] = Integer.parseInt(parts[i]);
                if (ip[i] > 255) return false;
            }
        } catch (NumberFormatException e) { return false; }
        return ip[0] == 10 || ip[0] == 127 || (ip[0] == 192 && ip[1] == 168)
                || (ip[0] == 172 && ip[1] >= 16 && ip[1] <= 31);
    }

    public static boolean sameOrigin(String server, String url) {
        try {
            URI expected = new URI(server), actual = new URI(url);
            return expected.getScheme().equalsIgnoreCase(actual.getScheme())
                    && expected.getHost().equalsIgnoreCase(actual.getHost())
                    && effectivePort(expected) == effectivePort(actual)
                    && actual.getRawUserInfo() == null;
        } catch (Exception e) { return false; }
    }

    private static int effectivePort(URI uri) {
        return uri.getPort() != -1 ? uri.getPort() : "https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80;
    }
}
