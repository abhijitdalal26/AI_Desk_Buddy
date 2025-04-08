#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>

// TFT Display Pins
#define TFT_CS    10
#define TFT_RST   8
#define TFT_DC    9
#define TFT_LED   6   // Backlight

// Create TFT instance
Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);

// Colors
#define FACE_COLOR      ST7735_YELLOW
#define TEXT_COLOR      ST7735_WHITE
#define HIGHLIGHT_COLOR ST7735_CYAN
#define TITLE_COLOR     ST7735_MAGENTA
#define BG_COLOR        ST7735_BLACK
#define OUTLINE_COLOR   ST7735_BLACK
#define EYE_COLOR       ST7735_BLACK
#define PUPIL_COLOR     ST7735_WHITE

void setup() {
  Serial.begin(9600);
  pinMode(TFT_LED, OUTPUT);
  analogWrite(TFT_LED, 255);

  tft.initR(INITR_BLACKTAB);
  tft.setRotation(1);

  drawInterface();
}

void loop() {
  delay(100);
}

void drawInterface() {
  tft.fillScreen(BG_COLOR);
  int screenWidth = tft.width();
  int screenHeight = tft.height();

  // Header
  tft.fillRect(0, 0, screenWidth, 18, TITLE_COLOR);
  tft.setTextColor(TEXT_COLOR);
  tft.setTextSize(2);

  int16_t x1, y1;
  uint16_t w, h;
  tft.getTextBounds("AI ASSISTANT", 0, 0, &x1, &y1, &w, &h);
  tft.setCursor((screenWidth - w) / 2, 2);
  tft.print("AI ASSISTANT");

  // Dotted lines
  for (int i = 0; i < screenWidth; i += 5) {
    tft.drawPixel(i, 19, HIGHLIGHT_COLOR);
    tft.drawPixel(i, screenHeight - 25, HIGHLIGHT_COLOR);
  }

  drawSmileyFace(screenWidth / 2, screenHeight / 2 - 5);

  // Footer
  const char* msg = "How can I help you?";
  tft.setTextSize(1);
  tft.getTextBounds(msg, 0, 0, &x1, &y1, &w, &h);
  int msgX = (screenWidth - w) / 2;
  int msgY = screenHeight - 18;

  tft.drawRoundRect(msgX - 6, msgY - 3, w + 12, h + 6, 4, HIGHLIGHT_COLOR);
  tft.setTextColor(HIGHLIGHT_COLOR);
  tft.setCursor(msgX, msgY);
  tft.print(msg);
}

void drawSmileyFace(int centerX, int centerY) {
  int radius = 36;
  int eyeOffsetX = 14;
  int eyeOffsetY = 10;
  int eyeRadius = 6;
  int pupilRadius = 3;

  // Face
  tft.fillCircle(centerX, centerY, radius, FACE_COLOR);
  tft.drawCircle(centerX, centerY, radius, OUTLINE_COLOR);

  // Eyes
  tft.fillCircle(centerX - eyeOffsetX, centerY - eyeOffsetY, eyeRadius + 1, PUPIL_COLOR); // outer white
  tft.fillCircle(centerX + eyeOffsetX, centerY - eyeOffsetY, eyeRadius + 1, PUPIL_COLOR);
  
  tft.fillCircle(centerX - eyeOffsetX, centerY - eyeOffsetY, eyeRadius, EYE_COLOR); // inner black
  tft.fillCircle(centerX + eyeOffsetX, centerY - eyeOffsetY, eyeRadius, EYE_COLOR);

  tft.fillCircle(centerX - eyeOffsetX + 1, centerY - eyeOffsetY - 1, pupilRadius, PUPIL_COLOR); // pupil shine
  tft.fillCircle(centerX + eyeOffsetX + 1, centerY - eyeOffsetY - 1, pupilRadius, PUPIL_COLOR);

  // Smile
  int smileWidth = 26;
  for (int x = -smileWidth; x <= smileWidth; x++) {
    float n = (float)x / smileWidth;
    float y = 10 * (1 - n * n);
    tft.drawPixel(centerX + x, centerY + (int)y + 10, OUTLINE_COLOR);
    tft.drawPixel(centerX + x, centerY + (int)y + 11, OUTLINE_COLOR);
  }
}