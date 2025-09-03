# 导入time模块
import time
# 导入 Pin 模块
from machine import Pin

#wroom
#pin_led = Pin(2, Pin.OUT)
#mini
#pin_led = Pin(8, Pin.OUT)


# 永真循环
while True:
    # 使 P12 输出高电平，点亮 LED
    pin_led.on()
    # 延时 0.5 秒
    time.sleep(0.5)
    # 使 P12 输出低电平，熄灭 LED
    pin_led.off()
    time.sleep(0.5)
