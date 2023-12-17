unsigned long startTime;
boolean timing;
unsigned long timeOut = 10000;
const byte alertPIN = 13;

void setup() {
  pinMode(alertPIN, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  
  if (Serial.available() > 0) {
    byte incomingByte = Serial.read();

    // Serial.print("I received: ");
    // Serial.println(incomingByte, DEC);
    if(incomingByte == 0xFF){
      startTime = millis();
      timing = true;
    }

  }

  if (timing == true)
  {
    if (millis() - startTime >= timeOut)
    {
      
      timing = false;
    }

    digitalWrite(alertPIN, HIGH);
  }else{
    digitalWrite(alertPIN, LOW);
  }
}
