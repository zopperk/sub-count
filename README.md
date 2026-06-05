# Sub Count — ESP32 Social Follower Display

Shows your friend's TikTok and Instagram follower counts on a 128×64 SSD1306 OLED connected to an ESP32.

## How it works

Social platforms block direct requests from microcontrollers, so this project uses a small Python server on your computer (or Raspberry Pi) to fetch the counts. The ESP32 polls that server over your local WiFi and updates the OLED.

```
┌─────────┐   WiFi/LAN   ┌──────────────┐   HTTPS   ┌─────────────────┐
│  ESP32  │ ──────────── │ Python server │ ──────── │ TikTok/Instagram│
│ + OLED  │   GET /counts│  (fetchers)   │          │                 │
└─────────┘              └──────────────┘          └─────────────────┘
```

## Hardware

| Part | Notes |
|------|-------|
| ESP32 dev board | Any ESP32-WROOM module |
| SSD1306 OLED | 128×64, I2C (not SPI) |
| Jumper wires | SDA → GPIO 21, SCL → GPIO 22, VCC → 3.3V, GND → GND |

## 1. Set up the server

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your friend's usernames:

```env
TIKTOK_USERNAME=their_tiktok_handle
INSTAGRAM_USERNAME=their_instagram_handle
```

### Start the server

```bash
python app.py
```

Test it: open `http://localhost:8080/counts` in a browser. You should see JSON like:

```json
{
  "updated_at": 1717459200,
  "platforms": [
    {"platform": "tiktok", "username": "friend", "followers": 125000, "display": "125.0K"},
    {"platform": "instagram", "username": "friend", "followers": 45000, "display": "45.0K"}
  ]
}
```

Note your computer's local IP (`ipconfig` on Windows, `ifconfig` on Mac/Linux) — the ESP32 needs it.

## 2. Flash the ESP32

### Arduino IDE setup

1. Install [Arduino IDE](https://www.arduino.cc/en/software) or use PlatformIO
2. Add ESP32 board support: **File → Preferences → Additional Board URLs**:
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
3. Install boards: **Tools → Board → Boards Manager** → search "esp32"
4. Install libraries via **Sketch → Include Library → Manage Libraries**:
   - `Adafruit SSD1306`
   - `Adafruit GFX Library`
   - `ArduinoJson` (by Benoit Blanchon)

### Configure

```bash
cd esp32/sub_count_display
cp secrets.h.example secrets.h
```

Edit `secrets.h`:

```cpp
#define WIFI_SSID "your_wifi"
#define WIFI_PASSWORD "your_password"
#define SERVER_HOST "192.168.1.100"  // your computer's IP
#define SERVER_PORT 8080
```

### Upload

1. Open `sub_count_display.ino` in Arduino IDE
2. Select your ESP32 board and COM port
3. Click **Upload**

The OLED will show TikTok and Instagram follower counts and refresh every 5 minutes.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| OLED blank | Check I2C wiring; try address `0x3D` instead of `0x3C` |
| WiFi failed | ESP32 only supports 2.4 GHz WiFi |
| HTTP error | Make sure server is running and `SERVER_HOST` is correct |
| Instagram/TikTok errors | Platforms change often; re-run server with `force=true`: `GET /counts?force=true` |

## Customization

- **Refresh rate**: change `REFRESH_INTERVAL_MS` in `secrets.h` (ESP32) and `CACHE_TTL_SECONDS` in `.env` (server)
- **Display layout**: edit `renderDisplay()` in the `.ino` file
- **Different OLED pins**: change `Wire.begin(21, 22)` in `setup()`
