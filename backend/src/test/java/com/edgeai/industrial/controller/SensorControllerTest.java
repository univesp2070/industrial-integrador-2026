package com.edgeai.industrial.controller;

import com.edgeai.industrial.config.SecurityConfig;
import com.edgeai.industrial.dto.SensorReadingDto;
import com.edgeai.industrial.repository.UserRepository;
import com.edgeai.industrial.security.JwtFilter;
import com.edgeai.industrial.security.JwtService;
import com.edgeai.industrial.security.UserDetailsServiceImpl;
import com.edgeai.industrial.service.SensorService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(SensorController.class)
@Import({SecurityConfig.class, JwtFilter.class, UserDetailsServiceImpl.class})
@WithMockUser
class SensorControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private SensorService sensorService;

    @MockBean
    private JwtService jwtService;

    @MockBean
    private UserRepository userRepository;

    @Test
    void getAnomaliesReturns200() throws Exception {
        SensorReadingDto reading = new SensorReadingDto(
                OffsetDateTime.now(), UUID.randomUUID(), "esp32-sim-001",
                "temperature", 78.5, "C", "anomaly", 0.92
        );
        when(sensorService.getAnomalies()).thenReturn(List.of(reading));

        mockMvc.perform(get("/api/sensors/anomalies"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].sensorType").value("temperature"))
                .andExpect(jsonPath("$[0].classification").value("anomaly"));
    }

    @Test
    void getLatestReturns200() throws Exception {
        when(sensorService.getLatestPerDevice()).thenReturn(List.of());

        mockMvc.perform(get("/api/sensors/latest"))
                .andExpect(status().isOk());
    }
}
