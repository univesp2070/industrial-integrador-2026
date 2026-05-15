/*
 * Edge AI Industrial — ESP32 Wokwi Simulator
 * UNIVESP PI-5
 *
 * Publica payload MQTT compatível com o backend Spring Boot:
 *   tópico: sensor/data/{device_id}
 *
 * Broker público: broker.emqx.io:1883 (sem autenticação)
 * Para conectar no broker local via Wokwi Gateway, altere MQTT_HOST.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <time.h>
#include <math.h>

// ── Pinos ──────────────────────────────────────────────────────────────────
#define DHT_PIN      4
#define DHT_TYPE     DHT22
#define VIB_PIN      A0
#define CUR_PIN      A3
#define LED_NORMAL   2
#define LED_ANOMALY  5
#define WEIGHT_PIN   A6

// ── Config WiFi / MQTT ─────────────────────────────────────────────────────
const char* WIFI_SSID  = "Wokwi-GUEST";
const char* WIFI_PASS  = "";
const char* MQTT_HOST  = "broker.emqx.io";  // troque por IP do gateway Wokwi para localhost
const int   MQTT_PORT  = 1883;
const char* DEVICE_ID  = "wokwi-shelf-001";

// ── Thresholds de anomalia ─────────────────────────────────────────────────
const float TEMP_ANOMALY  = 38.0;
const float VIB_ANOMALY   = 0.70;
const float CUR_ANOMALY   = 4.50;
const float PUBLISH_SEC   = 5.0;

const float WEIGHT_MAX_KG  = 10.0f;
const float PICK_THRESHOLD = 0.050f;

struct Product { const char* name; float unit_kg; float tolerance_kg; };
const Product CATALOG[] = {
  { "Parafuso M8",  0.025f, 0.008f },
  { "Porca M8",     0.010f, 0.004f },
  { "Arruela M8",   0.005f, 0.002f },
  { "Parafuso M12", 0.060f, 0.015f },
};
const int CATALOG_SIZE = 4;

struct PickResult { bool detected; const char* name; int qty; float delta; float conf; };

// ── Objetos ────────────────────────────────────────────────────────────────
DHT         dht(DHT_PIN, DHT_TYPE);
WiFiClient  wifiClient;
PubSubClient mqtt(wifiClient);

char sensorTopic[64];
char statusTopic[64];

// ── Helpers ────────────────────────────────────────────────────────────────
String isoTimestamp() {
  struct tm t;
  if (!getLocalTime(&t)) return "1970-01-01T00:00:00Z";
  char buf[30];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);
  return String(buf);
}

float readVibration() {
  int raw = analogRead(VIB_PIN);
  return 0.1f + (raw / 4095.0f) * 1.5f;
}

float readCurrent() {
  int raw = analogRead(CUR_PIN);
  return 1.0f + (raw / 4095.0f) * 6.0f;
}

float calcAnomalyScore(float temp, float vib, float cur) {
  float score = 0.0f;
  if (temp > TEMP_ANOMALY)  score += (temp - TEMP_ANOMALY) / 20.0f;
  if (vib  > VIB_ANOMALY)   score += (vib  - VIB_ANOMALY)  / 1.0f;
  if (cur  > CUR_ANOMALY)   score += (cur  - CUR_ANOMALY)  / 3.0f;
  return constrain(score / 3.0f + 0.05f, 0.0f, 1.0f);
}

float readWeight() {
  int raw = analogRead(WEIGHT_PIN);
  return (raw / 4095.0f) * WEIGHT_MAX_KG;
}

PickResult classifyPick(float prevWeight, float currentWeight) {
  float delta = prevWeight - currentWeight;
  if (delta < PICK_THRESHOLD) return { false, nullptr, 0, 0.0f, 0.0f };

  const Product* best = nullptr;
  float bestError = 1e9f;
  for (int i = 0; i < CATALOG_SIZE; i++) {
    int qty = max(1, (int)round(delta / CATALOG[i].unit_kg));
    float expected = qty * CATALOG[i].unit_kg;
    float error = fabsf(delta - expected);
    if (error < CATALOG[i].tolerance_kg * qty && error < bestError) {
      bestError = error;
      best = &CATALOG[i];
    }
  }

  if (!best) return { false, nullptr, 0, 0.0f, 0.0f };

  int qty = max(1, (int)round(delta / best->unit_kg));
  float expected = qty * best->unit_kg;
  float conf = constrain(1.0f - fabsf(delta - expected) / (best->unit_kg * qty), 0.0f, 1.0f);
  return { true, best->name, qty, delta, conf };
}

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(LED_NORMAL,  OUTPUT);
  pinMode(LED_ANOMALY, OUTPUT);
  digitalWrite(LED_NORMAL, LOW);
  digitalWrite(LED_ANOMALY, LOW);

  snprintf(sensorTopic, sizeof(sensorTopic), "sensor/data/%s", DEVICE_ID);
  snprintf(statusTopic, sizeof(statusTopic), "device/status/%s", DEVICE_ID);

  // WiFi
  Serial.printf("[WiFi] Conectando em %s...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.printf("\n[WiFi] Conectado! IP: %s\n", WiFi.localIP().toString().c_str());

  // NTP
  configTime(0, 0, "pool.ntp.org");
  Serial.println("[NTP] Sincronizando horario...");
  delay(2000);

  // MQTT
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(768);
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.printf("[MQTT] Conectando em %s...\n", MQTT_HOST);
    String clientId = String("wokwi-") + String(random(0xffff), HEX);
    if (mqtt.connect(clientId.c_str())) {
      Serial.println("[MQTT] Conectado!");
      // LWT — device offline
      StaticJsonDocument<128> lwt;
      lwt["device_id"] = DEVICE_ID;
      lwt["status"]    = "offline";
      char buf[128];
      serializeJson(lwt, buf);
      mqtt.publish(statusTopic, buf, true);
    } else {
      Serial.printf("[MQTT] Falha rc=%d — tentando novamente em 3s\n", mqtt.state());
      delay(3000);
    }
  }
}

void publishStatus(const char* status) {
  StaticJsonDocument<128> doc;
  doc["device_id"]        = DEVICE_ID;
  doc["status"]           = status;
  doc["firmware_version"] = "wokwi-1.0";
  doc["timestamp"]        = isoTimestamp();
  char buf[256];
  serializeJson(doc, buf);
  mqtt.publish(statusTopic, buf);
  Serial.printf("[STATUS] %s → %s\n", statusTopic, status);
}

// ── Loop ───────────────────────────────────────────────────────────────────
unsigned long lastPublish = 0;
float prevWeight = -1.0f;

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  unsigned long now = millis();
  if (now - lastPublish < (unsigned long)(PUBLISH_SEC * 1000)) return;
  lastPublish = now;

  // Leitura dos sensores
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();
  float vib  = readVibration();
  float cur  = readCurrent();
  float weight = readWeight();

  if (isnan(temp)) temp = 25.0f + sin(now / 10000.0f) * 3.0f;

  float score       = calcAnomalyScore(temp, vib, cur);
  bool  isAnomaly   = score > 0.5f;
  const char* cls   = isAnomaly ? "anomaly" : "normal";

  // LEDs
  digitalWrite(LED_NORMAL,  isAnomaly ? LOW  : HIGH);
  digitalWrite(LED_ANOMALY, isAnomaly ? HIGH : LOW);

  // Payload JSON
  StaticJsonDocument<768> doc;
  doc["device_id"] = DEVICE_ID;
  doc["timestamp"] = isoTimestamp();

  JsonObject sensors = doc.createNestedObject("sensors");
  JsonObject tempObj = sensors.createNestedObject("temperature");
  tempObj["value"] = round(temp * 100) / 100.0;
  tempObj["unit"]  = "C";

  JsonObject vibObj = sensors.createNestedObject("vibration");
  vibObj["value"]  = round(vib * 10000) / 10000.0;
  vibObj["unit"]   = "mm_s";

  JsonObject curObj = sensors.createNestedObject("current");
  curObj["value"]  = round(cur * 1000) / 1000.0;
  curObj["unit"]   = "A";

  JsonObject wgtObj = sensors.createNestedObject("weight");
  wgtObj["value"] = round(weight * 1000) / 1000.0;
  wgtObj["unit"]  = "kg";

  // Pick detection
  if (prevWeight >= 0.0f) {
    PickResult pick = classifyPick(prevWeight, weight);
    if (pick.detected) {
      JsonObject pe = doc.createNestedObject("pick_event");
      pe["detected"]        = true;
      pe["product_name"]    = pick.name;
      pe["quantity"]        = pick.qty;
      pe["weight_delta_kg"] = round(pick.delta * 10000) / 10000.0;
      pe["confidence"]      = round(pick.conf * 1000) / 1000.0;
      Serial.printf("[PICK] product=%s qty=%d delta=%.3fkg conf=%.2f\n",
                    pick.name, pick.qty, pick.delta, pick.conf);
    }
  }
  prevWeight = weight;

  JsonObject inf = doc.createNestedObject("inference");
  inf["classification"] = cls;
  inf["anomaly_score"]  = round(score * 1000) / 1000.0;
  inf["model_version"]  = "wokwi-v1";

  char buf[768];
  serializeJson(doc, buf);

  bool ok = mqtt.publish(sensorTopic, buf);
  Serial.printf("[SENSOR] temp=%.1fC vib=%.3f cur=%.2fA wgt=%.3fkg score=%.2f [%s] pub=%s\n",
                temp, vib, cur, weight, score, cls, ok ? "OK" : "FAIL");

  // Publica status a cada 30s
  static unsigned long lastStatus = 0;
  if (now - lastStatus > 30000) {
    publishStatus("online");
    lastStatus = now;
  }
}
