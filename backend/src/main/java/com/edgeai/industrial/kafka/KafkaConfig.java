package com.edgeai.industrial.kafka;

import com.edgeai.industrial.dto.SensorPayloadDto;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.config.TopicBuilder;
import org.springframework.kafka.core.*;
import org.springframework.kafka.support.serializer.JsonDeserializer;

import java.util.Map;

@Configuration
public class KafkaConfig {

    @Value("${spring.kafka.bootstrap-servers}")
    private String bootstrapServers;

    public static final String SENSOR_READINGS_TOPIC = "sensor-readings";

    @Bean
    public NewTopic sensorReadingsTopic() {
        return TopicBuilder.name(SENSOR_READINGS_TOPIC)
                .partitions(1)
                .replicas(1)
                .build();
    }

    @Bean
    public ConsumerFactory<String, SensorPayloadDto> sensorConsumerFactory() {
        JsonDeserializer<SensorPayloadDto> deserializer =
                new JsonDeserializer<>(SensorPayloadDto.class, false);
        deserializer.addTrustedPackages("com.edgeai.industrial.dto");

        return new DefaultKafkaConsumerFactory<>(
                Map.of(
                        "bootstrap.servers", bootstrapServers,
                        "group.id", "edge-ai-group",
                        "auto.offset.reset", "earliest"
                ),
                new StringDeserializer(),
                deserializer
        );
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, SensorPayloadDto> kafkaListenerContainerFactory(
            ConsumerFactory<String, SensorPayloadDto> consumerFactory) {
        ConcurrentKafkaListenerContainerFactory<String, SensorPayloadDto> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory);
        return factory;
    }
}
