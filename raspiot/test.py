import RPi.GPIO as GPIO
import time
import threading

def cb(channel):
    print('channel %s triggered' % channel)



class Test(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(3, GPIO.OUT)
        self.on = False

    def cb(self, channel):
        print 'channel #%s triggered' % channel
        if self.on:
            self.on = False
            GPIO.output(3, GPIO.LOW)
        else:
            self.on = True
            GPIO.output(3, GPIO.HIGH)

    def run(self):
        GPIO.add_event_detect(5, GPIO.RISING, self.cb, bouncetime=150)

        while True:
            time.sleep(0.1)

t = Test()
t.start()
t.join()

"""
GPIO.add_event_detect(5, GPIO.RISING, cb, bouncetime=150)
try:
    while True:
        time.sleep(0.1)
except:
    pass
"""

GPIO.cleanup()
