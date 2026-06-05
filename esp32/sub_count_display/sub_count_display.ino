#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include "secrets.h"

// Common wiring for 128x64 SSD1306 OLED on ESP32:
//   SDA -> GPIO 21
//   SCL -> GPIO 22
//
// Push button (cycles screens):
//   One leg -> GPIO 27
//   Other leg -> GND
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_ADDRESS 0x3C
#define BUTTON_PIN 27
#define BUTTON_DEBOUNCE_MS 50
#define MAX_LINE_CHARS 21

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

enum ScreenMode { SCREEN_FOLLOWERS, SCREEN_MOTIVATION };

const char* const MOTIVATION_QUOTES[] = {
  "The sky's the limit!",
  "The content grind continues",
  "Keep going, we're all proud of you!",
};
const int QUOTE_COUNT = sizeof(MOTIVATION_QUOTES) / sizeof(MOTIVATION_QUOTES[0]);

ScreenMode currentScreen = SCREEN_FOLLOWERS;
int currentQuoteIndex = 0;

struct PlatformCount {
  String platform;
  String display;
  bool valid;
};

PlatformCount counts[2];
int countSize = 0;
String lastUpdated = "--";
String statusMessage = "Starting...";

void showStatus(const String& line1, const String& line2 = "") {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(line1);
  if (line2.length() > 0) {
    display.println(line2);
  }
  display.display();
}

bool connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  showStatus("Connecting WiFi...", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    statusMessage = WiFi.localIP().toString();
    return true;
  }

  statusMessage = "WiFi failed";
  return false;
}

void pickRandomQuote() {
  currentQuoteIndex = random(0, QUOTE_COUNT);
}

void printWrappedText(const String& text, int16_t x, int16_t y) {
  String remaining = text;

  while (remaining.length() > 0) {
    if (remaining.length() <= MAX_LINE_CHARS) {
      display.setCursor(x, y);
      display.println(remaining);
      return;
    }

    int breakAt = MAX_LINE_CHARS;
    int spaceAt = remaining.lastIndexOf(' ', breakAt);
    if (spaceAt > 0) {
      breakAt = spaceAt;
    }

    display.setCursor(x, y);
    display.println(remaining.substring(0, breakAt));
    remaining = remaining.substring(breakAt);
    remaining.trim();
    y += 10;
  }
}

bool fetchCounts(bool showProgress = true) {
  if (!connectWiFi()) {
    return false;
  }

  String url = String("http://") + SERVER_HOST + ":" + String(SERVER_PORT) + "/counts";
  HTTPClient http;
  http.begin(url);
  http.setTimeout(10000);

  if (showProgress) {
    showStatus("Fetching counts...");
  }
  int httpCode = http.GET();

  if (httpCode != HTTP_CODE_OK) {
    statusMessage = "HTTP " + String(httpCode);
    http.end();
    return false;
  }

  String payload = http.getString();
  http.end();

  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (error) {
    statusMessage = "JSON error";
    return false;
  }

  countSize = 0;
  JsonArray platforms = doc["platforms"].as<JsonArray>();
  for (JsonObject item : platforms) {
    if (countSize >= 2) break;

    counts[countSize].platform = item["platform"].as<String>();
    counts[countSize].display = item["display"] | "--";
    counts[countSize].valid = !item["display"].isNull();
    countSize++;
  }

  unsigned long updatedAt = doc["updated_at"] | 0;
  if (updatedAt > 0) {
    lastUpdated = String(updatedAt);
  }

  statusMessage = "OK";
  return true;
}

void renderFollowersScreen() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("RICHARD'S FOLLOWERS");

  int y = 12;
  for (int i = 0; i < countSize; i++) {
    display.setCursor(0, y);
    display.print(counts[i].platform.substring(0, 3));
    display.print(": ");
    display.setTextSize(2);
    display.println(counts[i].valid ? counts[i].display : "ERR");
    display.setTextSize(1);
    y += 24;
  }

  display.display();
}

void renderMotivationScreen() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("MOTIVATION");
  printWrappedText(MOTIVATION_QUOTES[currentQuoteIndex], 0, 16);
  display.display();
}

void renderCurrentScreen() {
  if (currentScreen == SCREEN_FOLLOWERS) {
    renderFollowersScreen();
  } else {
    renderMotivationScreen();
  }
}

bool handleButtonPress() {
  static int lastReading = HIGH;
  static int stableReading = HIGH;
  static unsigned long lastDebounceTime = 0;

  int reading = digitalRead(BUTTON_PIN);
  if (reading != lastReading) {
    lastDebounceTime = millis();
    lastReading = reading;
  }

  if ((millis() - lastDebounceTime) > BUTTON_DEBOUNCE_MS && reading != stableReading) {
    stableReading = reading;
    if (stableReading == LOW) {
      return true;
    }
  }

  return false;
}

void cycleScreen() {
  if (currentScreen == SCREEN_FOLLOWERS) {
    currentScreen = SCREEN_MOTIVATION;
    pickRandomQuote();
  } else {
    currentScreen = SCREEN_FOLLOWERS;
  }
  renderCurrentScreen();
}

void setup() {
  Serial.begin(115200);
  randomSeed(micros());

  pinMode(BUTTON_PIN, INPUT_PULLUP);

  Wire.begin(21, 22);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
    Serial.println("SSD1306 allocation failed");
    for (;;) {
      delay(1000);
    }
  }

  showStatus("Sub Count", "Booting...");
  connectWiFi();
  fetchCounts();
  renderFollowersScreen();
}

void loop() {
  static unsigned long lastRefresh = 0;

  if (handleButtonPress()) {
    cycleScreen();
  }

  if (millis() - lastRefresh >= REFRESH_INTERVAL_MS) {
    bool showProgress = currentScreen == SCREEN_FOLLOWERS;
    if (fetchCounts(showProgress) && currentScreen == SCREEN_FOLLOWERS) {
      renderFollowersScreen();
    }
    lastRefresh = millis();
  }

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  delay(10);
}
