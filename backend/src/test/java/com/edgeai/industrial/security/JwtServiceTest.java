package com.edgeai.industrial.security;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class JwtServiceTest {

    private final JwtService jwtService = new JwtService(
            "dGVzdC1zZWNyZXQta2V5LXRoYXQtaXMtbG9uZy1lbm91Z2gtZm9yLUhTMjU2",
            86400000L
    );

    @Test
    void generateAndValidateToken() {
        String token = jwtService.generateToken("admin@edgeai.local");
        assertThat(jwtService.isTokenValid(token)).isTrue();
        assertThat(jwtService.extractEmail(token)).isEqualTo("admin@edgeai.local");
    }

    @Test
    void expiredTokenIsInvalid() {
        JwtService shortLived = new JwtService(
                "dGVzdC1zZWNyZXQta2V5LXRoYXQtaXMtbG9uZy1lbm91Z2gtZm9yLUhTMjU2",
                -1L
        );
        String token = shortLived.generateToken("user@test.com");
        assertThat(shortLived.isTokenValid(token)).isFalse();
    }
}
