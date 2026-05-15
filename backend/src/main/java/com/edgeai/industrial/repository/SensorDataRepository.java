package com.edgeai.industrial.repository;

import com.edgeai.industrial.dto.SensorReadingDto;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;
import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;

@Repository
@RequiredArgsConstructor
public class SensorDataRepository {

    private final JdbcTemplate jdbc;

    public void insert(OffsetDateTime time, UUID deviceId, String deviceName,
                       String sensorType, double value, String unit,
                       String classification, double anomalyScore) {
        jdbc.update("""
                INSERT INTO sensor_data
                    (time, device_id, sensor_type, value, unit, classification, anomaly_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                Timestamp.from(time.toInstant()), deviceId, sensorType,
                value, unit, classification, anomalyScore);
    }

    public List<SensorReadingDto> findByDeviceAndTimeRange(UUID deviceId,
                                                           OffsetDateTime from,
                                                           OffsetDateTime to) {
        return jdbc.query("""
                SELECT sd.time, sd.device_id, d.name AS device_name,
                       sd.sensor_type, sd.value, sd.unit,
                       sd.classification, sd.anomaly_score
                FROM sensor_data sd
                JOIN devices d ON d.id = sd.device_id
                WHERE sd.device_id = ?
                  AND sd.time BETWEEN ? AND ?
                ORDER BY sd.time DESC
                LIMIT 500
                """,
                rowMapper(),
                deviceId,
                Timestamp.from(from.toInstant()),
                Timestamp.from(to.toInstant()));
    }

    public List<SensorReadingDto> findLatestPerDevice() {
        return jdbc.query("""
                SELECT DISTINCT ON (sd.device_id)
                    sd.time, sd.device_id, d.name AS device_name,
                    sd.sensor_type, sd.value, sd.unit,
                    sd.classification, sd.anomaly_score
                FROM sensor_data sd
                JOIN devices d ON d.id = sd.device_id
                ORDER BY sd.device_id, sd.time DESC
                """,
                rowMapper());
    }

    public List<SensorReadingDto> findRecent(int minutes, int limit) {
        return jdbc.query("""
                SELECT sd.time, sd.device_id, d.name AS device_name,
                       sd.sensor_type, sd.value, sd.unit,
                       sd.classification, sd.anomaly_score
                FROM sensor_data sd
                JOIN devices d ON d.id = sd.device_id
                WHERE sd.time >= NOW() - (? * INTERVAL '1 minute')
                ORDER BY sd.time ASC
                LIMIT ?
                """,
                rowMapper(), minutes, limit);
    }

    public List<SensorReadingDto> findAnomalies(int limit) {
        return jdbc.query("""
                SELECT sd.time, sd.device_id, d.name AS device_name,
                       sd.sensor_type, sd.value, sd.unit,
                       sd.classification, sd.anomaly_score
                FROM sensor_data sd
                JOIN devices d ON d.id = sd.device_id
                WHERE sd.classification = 'anomaly'
                ORDER BY sd.time DESC
                LIMIT ?
                """,
                rowMapper(), limit);
    }

    private RowMapper<SensorReadingDto> rowMapper() {
        return (rs, rowNum) -> new SensorReadingDto(
                rs.getTimestamp("time").toInstant().atOffset(ZoneOffset.UTC),
                UUID.fromString(rs.getString("device_id")),
                rs.getString("device_name"),
                rs.getString("sensor_type"),
                rs.getDouble("value"),
                rs.getString("unit"),
                rs.getString("classification"),
                rs.getDouble("anomaly_score")
        );
    }
}
