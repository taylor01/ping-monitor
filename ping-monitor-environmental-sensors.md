# Environmental Sensor Component

## Overview

Battery-powered WiFi environmental sensors that report to the site agent via MQTT. Designed for multi-year battery life with intelligent reporting and Claude-powered battery monitoring via hardware fuel gauge.

---

## Hardware

### Microcontroller: Unexpected Maker TinyS3[D]

**Product:** [TinyS3[D]](https://unexpectedmaker.com/shop.html#!/TinyS3-D/p/759468759) (Series D)

| Spec | Value |
|------|-------|
| MCU | ESP32-S3FN8 |
| Flash | 8MB (internal) |
| PSRAM | 8MB (external) |
| GPIO | 17 |
| Deep Sleep | ~5-10µA |
| Size | 35mm x 17.8mm |
| Battery | Header + JST pads on bottom |
| Charging | Built-in via USB-C (~250-500mA) |
| **Fuel Gauge** | **I2C battery monitor with RTC-IO interrupt** |
| Antenna | Dual - onboard + u.FL (software switchable) |
| ESD Protection | Yes |
| Price | ~$20-22 USD |

**Why TinyS3[D] (Series D):**
- **I2C Fuel Gauge** - Accurate state-of-charge, not just voltage guessing
- Fuel gauge interrupt on RTC-IO - can wake ESP32 on low battery
- Built-in LiPo charging circuit (no separate charger needed)
- Dual antenna with software RF switch (better range options)
- ESD protection
- JST battery pads for clean wiring
- USB-C for programming and charging
- Compact form factor for enclosures

**Fuel Gauge Benefits:**
- Accurate remaining capacity estimation
- Tracks charge cycles
- Temperature-compensated readings
- Hardware interrupt at configurable threshold
- No ADC calibration needed

---

### Battery: Dual 18650 Li-ion (6000mAh total)

**Configuration:** 2x 18650 cells wired in parallel

| Spec | Value |
|------|-------|
| Chemistry | Li-ion |
| Nominal Voltage | 3.7V |
| Full Charge | 4.2V |
| Cutoff | 3.0V |
| Capacity | 6000mAh (2x 3000mAh parallel) |
| Price | ~$10-16 USD (2 cells) |

**Recommended cells:**
- Samsung 30Q (3000mAh)
- Sony VTC6 (3000mAh)
- Panasonic NCR18650B (3400mAh)
- Any protected 18650 from reputable source

**Why dual cells:**
- 5-minute reporting interval (more responsive)
- ~1.5-2 year battery life
- Self-discharge becomes the limiting factor, not capacity
- Parallel wiring keeps voltage at 3.7V nominal (same as single cell)

**Wiring (parallel):**
```
Cell 1 (+) ──┬── BAT+ on TinyS3[D]
Cell 2 (+) ──┘

Cell 1 (-) ──┬── GND on TinyS3[D]
Cell 2 (-) ──┘
```

**Battery holder:** Dual 18650 holder with parallel wiring (~$2) or 2x single holders wired together. Solder JST connector or wire directly to TinyS3[D] BAT+/GND pads.

**Charging:** USB-C on TinyS3[D] charges at ~250-500mA. Full charge from empty takes ~12-14 hours for dual cells. Given ~1.5-2 year runtime, this is a rare event.

**Protection:** Use protected cells (built-in over-discharge cutoff) OR rely on the fuel gauge interrupt to alert/shutdown before critical levels.

---

### Sensor: BME280

| Spec | Value |
|------|-------|
| Temperature | -40°C to +85°C, ±1°C accuracy |
| Humidity | 0-100% RH, ±3% accuracy |
| Pressure | 300-1100 hPa, ±1 hPa accuracy |
| Interface | I2C (0x76 or 0x77) |
| Supply | 1.8-3.3V |
| Sleep Current | <1µA |
| Price | ~$3-5 USD |

**Wiring to TinyS3[D]:**

| BME280 | TinyS3[D] |
|--------|-----------|
| VIN | 3V3 |
| GND | GND |
| SCL | GPIO9 (default I2C) |
| SDA | GPIO8 (default I2C) |

Note: Fuel gauge is also on I2C bus - no conflict, different address.

---

### Bill of Materials

| Component | Source | Price |
|-----------|--------|-------|
| TinyS3[D] | Unexpected Maker | $22 |
| BME280 breakout | AliExpress/Amazon | $3 |
| 18650 protected cells (2x) | 18650batterystore.com | $12 |
| Dual 18650 holder (parallel) | Amazon/AliExpress | $2 |
| JST-PH connector (optional) | Amazon | $0.50 |
| Enclosure (3D printed or project box) | -- | $3 |
| **Total** | | **~$42** |

For multiple sensors, buy BME280 and battery holders in bulk—drops to ~$35/sensor.

---

## Firmware

### Optimizations Applied

1. **Static IP** - Skip DHCP, saves ~1 second per wake
2. **Fast reconnect** - Cache WiFi channel and BSSID in RTC memory
3. **Send on change** - Skip transmission if readings haven't changed significantly
4. **Forced report interval** - Ensure at least one report per hour even if unchanged
5. **Aggressive sleep** - WiFi off before deep sleep
6. **Fuel gauge integration** - Read accurate state-of-charge from hardware

### Configuration

```cpp
// ========== CONFIG ==========
const char* WIFI_SSID     = "your-ssid";
const char* WIFI_PASS     = "your-password";
const char* MQTT_SERVER   = "192.168.1.155";  // Site agent host
const char* SENSOR_ID     = "cabin-garage";   // Unique per sensor

// Static IP (must be reserved in DHCP/router)
IPAddress ip(192, 168, 1, 200);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(192, 168, 1, 1);

// Timing
const int SLEEP_MINUTES       = 5;    // Report interval (5 min for responsive monitoring)
const int MAX_SILENT_CYCLES   = 12;   // Force report every hour (12 x 5 min)
const int WIFI_TIMEOUT_MS     = 5000; // Give up connecting after 5s

// Change thresholds
const float TEMP_CHANGE_THRESHOLD  = 0.5;  // °F
const float HUMID_CHANGE_THRESHOLD = 2.0;  // %
```

### Full Firmware

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_BME280.h>
#include <ArduinoJson.h>
#include <Wire.h>

// For TinyS3[D] fuel gauge (MAX17048 or similar)
// Install: Adafruit_MAX1704X library
#include <Adafruit_MAX1704X.h>

// ========== CONFIG ==========
const char* WIFI_SSID     = "your-ssid";
const char* WIFI_PASS     = "your-password";
const char* MQTT_SERVER   = "192.168.1.155";
const char* SENSOR_ID     = "cabin-garage";

IPAddress ip(192, 168, 1, 200);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(192, 168, 1, 1);

const int SLEEP_MINUTES       = 5;
const int MAX_SILENT_CYCLES   = 12;
const int WIFI_TIMEOUT_MS     = 5000;

const float TEMP_CHANGE_THRESHOLD  = 0.5;
const float HUMID_CHANGE_THRESHOLD = 2.0;

// ========== RTC MEMORY (survives deep sleep) ==========
RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR int silentCycles = 0;
RTC_DATA_ATTR float lastTemp = -999;
RTC_DATA_ATTR float lastHumid = -999;
RTC_DATA_ATTR uint8_t savedBSSID[6] = {0};
RTC_DATA_ATTR int32_t savedChannel = 0;

// ========== GLOBALS ==========
Adafruit_BME280 bme;
Adafruit_MAX17048 fuelGauge;
WiFiClient espClient;
PubSubClient mqtt(espClient);
bool hasFuelGauge = false;

// ========== FUNCTIONS ==========

void initFuelGauge() {
  if (fuelGauge.begin()) {
    hasFuelGauge = true;
  }
}

float readBatteryVoltage() {
  if (hasFuelGauge) {
    return fuelGauge.cellVoltage();
  }
  // Fallback to ADC if fuel gauge not available
  analogSetAttenuation(ADC_11db);
  int raw = analogRead(34);
  return (raw / 4095.0) * 3.3 * 2;
}

float readBatteryPercent() {
  if (hasFuelGauge) {
    return fuelGauge.cellPercent();
  }
  return -1;  // Unknown
}

bool connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.config(ip, gateway, subnet, dns);
  
  // Fast reconnect using cached channel/BSSID
  if (savedChannel != 0) {
    WiFi.begin(WIFI_SSID, WIFI_PASS, savedChannel, savedBSSID, true);
  } else {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
  }
  
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - start > WIFI_TIMEOUT_MS) {
      return false;
    }
    delay(50);
  }
  
  // Cache for next boot
  savedChannel = WiFi.channel();
  memcpy(savedBSSID, WiFi.BSSID(), 6);
  
  return true;
}

bool shouldReport(float temp, float humid) {
  if (lastTemp == -999) return true;  // First boot
  if (silentCycles >= MAX_SILENT_CYCLES) return true;  // Force hourly
  if (abs(temp - lastTemp) >= TEMP_CHANGE_THRESHOLD) return true;
  if (abs(humid - lastHumid) >= HUMID_CHANGE_THRESHOLD) return true;
  return false;
}

void deepSleep() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  esp_wifi_stop();
  
  esp_sleep_enable_timer_wakeup(SLEEP_MINUTES * 60ULL * 1000000ULL);
  esp_deep_sleep_start();
}

// ========== MAIN ==========

void setup() {
  bootCount++;
  
  // Init I2C (shared by BME280 and fuel gauge)
  Wire.begin(8, 9);  // SDA=8, SCL=9 for TinyS3[D]
  
  // Init fuel gauge
  initFuelGauge();
  
  // Init environmental sensor
  if (!bme.begin(0x76)) {
    deepSleep();  // Sensor failed, retry next cycle
  }
  
  bme.takeForcedMeasurement();
  
  // Read values
  float temp_c = bme.readTemperature();
  float temp_f = temp_c * 9.0 / 5.0 + 32.0;
  float humid = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;
  float battery_v = readBatteryVoltage();
  float battery_pct = readBatteryPercent();
  
  // Skip TX if no significant change
  if (!shouldReport(temp_f, humid)) {
    silentCycles++;
    deepSleep();
    return;
  }
  
  // Connect WiFi
  if (!connectWiFi()) {
    deepSleep();  // Failed, retry next cycle
    return;
  }
  
  // Build JSON payload
  StaticJsonDocument<300> doc;
  doc["sensor_id"] = SENSOR_ID;
  doc["temp_f"] = round(temp_f * 10) / 10.0;
  doc["temp_c"] = round(temp_c * 10) / 10.0;
  doc["humidity"] = round(humid * 10) / 10.0;
  doc["pressure_hpa"] = round(pressure * 10) / 10.0;
  doc["battery_v"] = round(battery_v * 100) / 100.0;
  if (battery_pct >= 0) {
    doc["battery_pct"] = round(battery_pct * 10) / 10.0;
  }
  doc["rssi"] = WiFi.RSSI();
  doc["boot"] = bootCount;
  
  char payload[300];
  serializeJson(doc, payload);
  char topic[64];
  snprintf(topic, sizeof(topic), "sensors/env/%s", SENSOR_ID);
  
  // Publish
  mqtt.setServer(MQTT_SERVER, 1883);
  if (mqtt.connect(SENSOR_ID)) {
    mqtt.publish(topic, payload, true);
    mqtt.loop();
    delay(50);
    mqtt.disconnect();
  }
  
  // Update state
  lastTemp = temp_f;
  lastHumid = humid;
  silentCycles = 0;
  
  deepSleep();
}

void loop() {
  // Never reached
}
```

### PlatformIO Configuration

```ini
; platformio.ini
[env:tinys3]
platform = espressif32
board = tinys3
framework = arduino
monitor_speed = 115200

lib_deps =
    adafruit/Adafruit BME280 Library@^2.2.2
    adafruit/Adafruit MAX1704X@^1.0.0
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^6.21.3

build_flags =
    -DARDUINO_USB_MODE=1
    -DARDUINO_USB_CDC_ON_BOOT=1
```

---

## Power Analysis

### Per-Cycle Energy (5-minute interval)

| State | Current | Duration | Energy |
|-------|---------|----------|--------|
| Deep sleep | 10µA | 5 min | 0.8µAh |
| Wake + sensor + fuel gauge | 20mA | 50ms | 0.3µAh |
| WiFi connect (fast) | 150mA | 500ms | 20.8µAh |
| MQTT publish | 150mA | 100ms | 4.2µAh |
| **Full TX cycle** | | | **~26µAh** |
| **Silent cycle (no change)** | | | **~1µAh** |

### Daily/Monthly Usage

| Metric | Value |
|--------|-------|
| Cycles per day | 288 |
| Full TX cycles (~50%) | 144 |
| Silent cycles (~50%) | 144 |
| Daily sensor usage | ~4.5mAh |
| Daily self-discharge | ~5mAh |
| **Total daily drain** | **~9.5mAh** |

### Battery Life Estimates

| Configuration | Capacity | Estimated Life |
|---------------|----------|----------------|
| Single 18650 | 3000mAh | 10-12 months |
| **Dual 18650 (parallel)** | **6000mAh** | **1.5-2 years** |
| Dual 18650 + solar top-up | 6000mAh | Indefinite |

At 5-minute intervals with dual cells, self-discharge (~2-3%/month) becomes roughly equal to actual sensor usage. This is near-optimal—going to larger batteries yields diminishing returns.

### Interval Comparison (Dual 18650)

| Interval | Cycles/Day | Daily Draw | Battery Life |
|----------|------------|------------|--------------|
| 1 min | 1440 | ~25mAh | 6-8 months |
| **5 min** | **288** | **~9.5mAh** | **1.5-2 years** |
| 15 min | 96 | ~6mAh | 2+ years (self-discharge limited) |
| 30 min | 48 | ~5.5mAh | 2+ years (self-discharge limited) |

**5 minutes is the sweet spot** - responsive enough to catch temperature swings (HVAC issues, freezer problems) while still achieving multi-year battery life.

---

## MQTT Integration

### Topic Structure

```
sensors/
├── env/                      # Environmental sensors
│   ├── cabin-garage          # Site-location naming
│   ├── cabin-crawlspace
│   ├── cabin-attic
│   └── home-basement
├── water/                    # Future: water leak sensors
│   └── cabin-water-heater
└── power/                    # Future: power monitoring
    └── cabin-main-panel
```

### Message Format

```json
{
  "sensor_id": "cabin-garage",
  "temp_f": 68.5,
  "temp_c": 20.3,
  "humidity": 45.2,
  "pressure_hpa": 1013.5,
  "battery_v": 3.85,
  "battery_pct": 72.5,
  "rssi": -62,
  "boot": 1547
}
```

Note: `battery_pct` is provided by the fuel gauge and is more accurate than voltage-based estimates.

### Site Agent MQTT Collector

The site agent subscribes to `sensors/#` and forwards readings to the Rails headend:

```python
class MQTTCollector:
    def __init__(self, host: str, topics: list[str]):
        self.host = host
        self.topics = topics
        self.readings = {}
    
    async def run(self):
        async with aiomqtt.Client(self.host) as client:
            for topic in self.topics:
                await client.subscribe(topic)
            
            async for message in client.messages:
                payload = json.loads(message.payload.decode())
                sensor_id = payload.get("sensor_id")
                
                self.readings[sensor_id] = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "topic": str(message.topic),
                    **payload
                }
                
                await result_queue.put({
                    "type": "sensor",
                    "data": self.readings[sensor_id]
                })
```

---

## Rails Integration

### Model

```ruby
# app/models/sensor_reading.rb
class SensorReading < ApplicationRecord
  belongs_to :site
  
  validates :sensor_id, presence: true
  validates :battery_v, numericality: { greater_than: 0 }, allow_nil: true
  validates :battery_pct, numericality: { in: 0..100 }, allow_nil: true
  
  scope :latest_per_sensor, -> {
    select("DISTINCT ON (sensor_id) *")
      .order(:sensor_id, created_at: :desc)
  }
  
  scope :for_sensor, ->(sensor_id) { where(sensor_id: sensor_id) }
end
```

### Migration

```ruby
class CreateSensorReadings < ActiveRecord::Migration[8.0]
  def change
    create_table :sensor_readings do |t|
      t.references :site, null: false, foreign_key: true
      t.string :sensor_id, null: false
      t.float :temp_f
      t.float :temp_c
      t.float :humidity
      t.float :pressure_hpa
      t.float :battery_v
      t.float :battery_pct      # From fuel gauge
      t.integer :rssi
      t.integer :boot_count
      t.string :topic
      
      t.timestamps
    end
    
    add_index :sensor_readings, [:site_id, :sensor_id, :created_at]
    add_index :sensor_readings, [:sensor_id, :created_at]
  end
end
```

### API Endpoint

```ruby
# POST /api/v1/measurements
# Accepts both ping results and sensor readings

class Api::V1::MeasurementsController < ApplicationController
  def create
    params[:measurements].each do |m|
      case m[:type]
      when "ping"
        Measurement.create!(measurement_params(m))
      when "sensor"
        SensorReading.create!(sensor_params(m))
      end
    end
    
    head :created
  end
  
  private
  
  def sensor_params(m)
    m.slice(:sensor_id, :temp_f, :temp_c, :humidity, 
            :pressure_hpa, :battery_v, :battery_pct, :rssi, :boot_count)
      .merge(site: current_site)
  end
end
```

---

## Claude NOC Battery Monitoring

### Thresholds (Fuel Gauge Percentage)

| Percentage | State | Action |
|------------|-------|--------|
| 80-100% | Full | Recently charged |
| 50-80% | Healthy | Normal operation |
| 25-50% | OK | Monitor trend |
| 15-25% | Warning | Alert, plan maintenance |
| 5-15% | Critical | Swap/charge soon |
| <5% | Dead | May not wake reliably |

### Voltage Thresholds (Fallback)

| Voltage | State | Action |
|---------|-------|--------|
| 4.0-4.2V | Full | Recently charged |
| 3.7-4.0V | Healthy | Normal operation |
| 3.5-3.7V | OK | Monitor trend |
| 3.4-3.5V | Warning | Alert, plan maintenance |
| 3.2-3.4V | Critical | Swap immediately |
| <3.2V | Dead | Too late, may not boot |

### Anomaly Detection

```ruby
# app/services/sensor_anomaly_detector.rb
class SensorAnomalyDetector
  # Percentage-based (preferred when fuel gauge available)
  BATTERY_PCT_WARNING  = 25
  BATTERY_PCT_CRITICAL = 10
  
  # Voltage-based (fallback)
  BATTERY_V_WARNING  = 3.5
  BATTERY_V_CRITICAL = 3.3
  
  TEMP_MIN = 32   # Freeze warning
  TEMP_MAX = 95   # Heat warning
  
  HUMIDITY_MIN = 20  # Very dry
  HUMIDITY_MAX = 80  # Mold risk
  
  STALE_THRESHOLD = 30.minutes  # No report in 30 min = problem (5 min interval)
  
  def check(reading)
    anomalies = []
    
    # Battery (prefer percentage if available)
    if reading.battery_pct
      if reading.battery_pct < BATTERY_PCT_CRITICAL
        anomalies << { type: :battery_critical, value: reading.battery_pct, unit: '%' }
      elsif reading.battery_pct < BATTERY_PCT_WARNING
        anomalies << { type: :battery_warning, value: reading.battery_pct, unit: '%' }
      end
    elsif reading.battery_v
      if reading.battery_v < BATTERY_V_CRITICAL
        anomalies << { type: :battery_critical, value: reading.battery_v, unit: 'V' }
      elsif reading.battery_v < BATTERY_V_WARNING
        anomalies << { type: :battery_warning, value: reading.battery_v, unit: 'V' }
      end
    end
    
    # Temperature
    if reading.temp_f && reading.temp_f < TEMP_MIN
      anomalies << { type: :freeze_warning, value: reading.temp_f }
    elsif reading.temp_f && reading.temp_f > TEMP_MAX
      anomalies << { type: :heat_warning, value: reading.temp_f }
    end
    
    # Humidity
    if reading.humidity && reading.humidity > HUMIDITY_MAX
      anomalies << { type: :humidity_high, value: reading.humidity }
    end
    
    anomalies
  end
  
  def check_stale_sensors(site)
    site.sensor_readings
        .latest_per_sensor
        .where("created_at < ?", STALE_THRESHOLD.ago)
        .pluck(:sensor_id)
  end
end
```

### Claude Analysis Prompt

```ruby
# When battery anomalies accumulate
context = <<~CONTEXT
  ## Sensor Battery Report
  
  Site: cabin
  Generated: #{Time.current}
  
  | Sensor | Charge | Voltage | Trend | Est. Remaining |
  |--------|--------|---------|-------|----------------|
  | cabin-garage | 23% | 3.52V | -2%/week | ~4 weeks |
  | cabin-crawlspace | 68% | 3.85V | stable | ~6 months |
  | cabin-attic | 18% | 3.45V | -5%/week | ~2 weeks ⚠️ |
  
  Note: cabin-attic discharge rate is abnormal (2.5x expected).
  Boot count increasing faster than expected.
  RSSI has degraded from -55 to -72 over past month.
CONTEXT

# Claude response might be:
# "cabin-attic sensor has abnormal battery drain (18%, dropping 5%/week vs 
#  expected 2%/week). The degrading RSSI (-55 → -72) suggests it's struggling 
#  to connect to WiFi, causing repeated connection attempts that drain the 
#  battery faster. Recommend:
#  1. Check if nearest AP (Upstairs-Hallway-AP) is functioning
#  2. Consider relocating sensor or adding AP coverage
#  3. Schedule battery swap within 2 weeks
#  4. cabin-garage also at 23% - add to same maintenance visit
#  5. Both sensors can be charged via USB-C, ~12-14 hours for full charge"
```

---

## Deployment Checklist

### Per Sensor

- [ ] Flash firmware with unique SENSOR_ID
- [ ] Configure static IP (reserve in router/DHCP)
- [ ] Test MQTT publishing locally
- [ ] Verify fuel gauge reads battery percentage correctly
- [ ] Wire dual 18650 cells in parallel
- [ ] Verify voltage shows ~3.7-4.2V (parallel = same as single cell voltage)
- [ ] Install in enclosure
- [ ] Mount in location
- [ ] Verify first reading appears in site agent logs
- [ ] Confirm data flows to Rails headend
- [ ] Add to sensor inventory in Rails

### Infrastructure

- [ ] Mosquitto MQTT broker running on site agent host
- [ ] Site agent subscribed to `sensors/#`
- [ ] Rails endpoint accepting sensor readings
- [ ] Sensor anomaly detection job scheduled
- [ ] Battery monitoring thresholds configured (percentage-based)
- [ ] Slack alerts for battery warnings

---

## Future Enhancements

### Additional Sensor Types

| Sensor | Use Case | Estimated Addition |
|--------|----------|-------------------|
| Water leak (GPIO) | Basement, water heater | $2 |
| Door/window (reed switch) | Security, open alerts | $1 |
| Light level (BH1750) | Occupancy inference | $2 |
| Air quality (SGP30) | CO2, VOC | $8 |
| Soil moisture | Garden, plants | $2 |

### Low Battery Wake Interrupt

The TinyS3[D] fuel gauge has an interrupt pin connected to RTC-IO. This allows:

```cpp
// Configure fuel gauge to trigger interrupt at 10%
fuelGauge.setAlertVoltages(3.2, 4.2);  // Min/max
fuelGauge.enableAlert();

// Configure ESP32 to wake on fuel gauge interrupt
esp_sleep_enable_ext0_wakeup(FUEL_GAUGE_INT_PIN, LOW);
```

Use case: Sensor can sleep indefinitely and wake ONLY when battery is critical, then send a final "battery critical" message before shutting down.

### OTA Updates

Add ArduinoOTA or custom HTTP OTA to update firmware without physical access:

```cpp
// Check for update flag in MQTT message
// Download and flash new firmware
// Requires enough battery for extended wake time (~30s)
```

### Solar Top-Up

For indefinite runtime, add a small 5V 1W solar panel:
- Connect to USB-C or dedicated solar input
- TinyS3[D] handles charging automatically
- Even indirect light provides enough to offset ~10mAh/day usage

---

## References

- [TinyS3[D] Documentation](https://esp32s3.com/tinys3d.html)
- [Series D Announcement](https://unexpectedmaker.com/)
- [BME280 Datasheet](https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/)
- [MAX17048 Fuel Gauge](https://www.maximintegrated.com/en/products/power/battery-management/MAX17048.html)
- [ESP32 Deep Sleep Modes](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/sleep_modes.html)
- [PubSubClient Library](https://pubsubclient.knolleary.net/)
- [Mosquitto MQTT Broker](https://mosquitto.org/)
