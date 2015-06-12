#!/usr/bin/python

import time

# This is to emulate E:D running in the background

running = True
while running:
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        running = False
