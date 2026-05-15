#include <Arduino.h>
#include "EdgeNode.h"

static EdgeNode node;

void setup() { node.begin(); }
void loop()  { node.loop();  }
