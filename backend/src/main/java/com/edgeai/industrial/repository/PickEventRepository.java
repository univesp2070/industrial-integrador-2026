package com.edgeai.industrial.repository;

import com.edgeai.industrial.dto.PickEventDto;
import com.edgeai.industrial.dto.ProductDemandDto;
import com.edgeai.industrial.dto.SensorPayloadDto;
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
public class PickEventRepository {

    private final JdbcTemplate jdbc;

    public void save(UUID deviceId, OffsetDateTime time, SensorPayloadDto.PickEvent pick) {
        jdbc.update("""
                INSERT INTO pick_events
                    (time, device_id, product_name, quantity, weight_delta_kg, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                Timestamp.from(time.toInstant()),
                deviceId,
                pick.getProductName(),
                pick.getQuantity(),
                pick.getWeightDeltaKg(),
                pick.getConfidence());
    }

    public List<PickEventDto> findRecent(int hours, int limit) {
        return jdbc.query("""
                SELECT pe.time, pe.device_id, d.name AS device_name,
                       pe.product_name, pe.quantity, pe.weight_delta_kg, pe.confidence
                FROM pick_events pe
                JOIN devices d ON d.id = pe.device_id
                WHERE pe.time >= NOW() - (? * INTERVAL '1 hour')
                ORDER BY pe.time DESC
                LIMIT ?
                """,
                pickEventRowMapper(), hours, limit);
    }

    public List<ProductDemandDto> findDemandAggregate(int hours) {
        return jdbc.query("""
                SELECT product_name,
                       COUNT(*)       AS total_picks,
                       SUM(quantity)  AS total_quantity,
                       MAX(time)      AS last_pick
                FROM pick_events
                WHERE time >= NOW() - (? * INTERVAL '1 hour')
                GROUP BY product_name
                ORDER BY total_picks DESC
                """,
                demandRowMapper(), hours);
    }

    private RowMapper<PickEventDto> pickEventRowMapper() {
        return (rs, rowNum) -> new PickEventDto(
                rs.getTimestamp("time").toInstant().atOffset(ZoneOffset.UTC),
                UUID.fromString(rs.getString("device_id")),
                rs.getString("device_name"),
                rs.getString("product_name"),
                rs.getInt("quantity"),
                rs.getDouble("weight_delta_kg"),
                rs.getDouble("confidence")
        );
    }

    private RowMapper<ProductDemandDto> demandRowMapper() {
        return (rs, rowNum) -> new ProductDemandDto(
                rs.getString("product_name"),
                rs.getLong("total_picks"),
                rs.getLong("total_quantity"),
                rs.getTimestamp("last_pick").toInstant().atOffset(ZoneOffset.UTC)
        );
    }
}
