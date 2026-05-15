package com.edgeai.industrial.domain;

import org.junit.jupiter.api.Test;

import java.time.OffsetDateTime;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class DeviceTest {

    @Test
    void deviceIsOnlineWhenStatusIsOnline() {
        Device device = new Device();
        device.setStatus("online");
        assertThat(device.getStatus()).isEqualTo("online");
    }

    @Test
    void defaultStatusIsInactive() {
        Device device = new Device();
        assertThat(device.getStatus()).isEqualTo("inactive");
    }

    @Test
    void timestampsAreNullBeforeOnCreate() {
        Device device = new Device();
        assertThat(device.getCreatedAt()).isNull();
        assertThat(device.getUpdatedAt()).isNull();
    }

    @Test
    void onCreateSetsTimestamps() {
        Device device = new Device();
        device.onCreate();
        assertThat(device.getCreatedAt()).isNotNull();
        assertThat(device.getUpdatedAt()).isNotNull();
    }

    @Test
    void onCreateDoesNotOverwriteExistingTimestamps() {
        Device device = new Device();
        OffsetDateTime fixedTime = OffsetDateTime.parse("2026-01-01T00:00:00Z");
        device.setCreatedAt(fixedTime);
        device.setUpdatedAt(fixedTime);
        device.onCreate();
        assertThat(device.getCreatedAt()).isEqualTo(fixedTime);
        assertThat(device.getUpdatedAt()).isEqualTo(fixedTime);
    }

    @Test
    void equalityIsBasedOnIdOnly() {
        UUID sharedId = UUID.randomUUID();

        Device d1 = new Device();
        d1.setId(sharedId);
        d1.setName("Alpha");

        Device d2 = new Device();
        d2.setId(sharedId);
        d2.setName("Beta");

        assertThat(d1).isEqualTo(d2);
    }

    @Test
    void devicesWithDifferentIdsAreNotEqual() {
        Device d1 = new Device();
        d1.setId(UUID.randomUUID());

        Device d2 = new Device();
        d2.setId(UUID.randomUUID());

        assertThat(d1).isNotEqualTo(d2);
    }
}
