package com.spendwise.app;

/** No Android or JUnit dependency: run with javac/java -ea. */
public final class ServerAddressTest {
    public static void main(String[] args) {
        assert ServerAddress.normalize(" http://192.168.1.20:3000/ ",true).equals("http://192.168.1.20:3000");
        assert ServerAddress.normalize("https://EXAMPLE.com",false).equals("https://example.com");
        assert ServerAddress.normalize("http://10.0.2.2:3000",true).equals("http://10.0.2.2:3000");
        assert ServerAddress.sameOrigin("https://example.com","https://example.com:443/api/export/report");
        assert !ServerAddress.sameOrigin("https://example.com","http://example.com");
        assert !ServerAddress.sameOrigin("https://example.com","https://example.com.evil.test");
        assert !ServerAddress.sameOrigin("https://example.com","https://example.com@evil.test");
        assert !ServerAddress.sameOrigin("http://192.168.1.20:3000","http://192.168.1.20:8000");
        String[] bad={"javascript:alert(1)","file:///data/local","http://example.com","http://192.168.1.20.evil.test", "http://192.168.999.1", "https://user:pass@example.com", "https://example.com/path", "https://example.com?key=secret", "https://example.com#fragment", "https://example.com:99999", "https://example.com:0"};
        for(String input:bad) {
            boolean rejected=false; try { ServerAddress.normalize(input,true); } catch(IllegalArgumentException expected) { rejected=true; }
            assert rejected : input;
        }
        boolean rejected=false; try { ServerAddress.normalize("http://192.168.1.20:3000",false); } catch(IllegalArgumentException expected) { rejected=true; }
        assert rejected : "Release must require HTTPS";
        System.out.println("PASS: server address validation, private HTTP policy, HTTPS policy and origin isolation.");
    }
}
