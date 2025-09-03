import time
from machine import Pin
import neopixel

# 定义 NeoPixel 引脚和数量
# RGB_BUILTIN_PIN = 21  # 数据引脚，确保连接正确
RGB_BUILTIN_PIN = 38
RGB_BUILTIN_COUNT = 1  # 只有一个 NeoPixel

# 初始化 NeoPixel
np = neopixel.NeoPixel(Pin(RGB_BUILTIN_PIN), RGB_BUILTIN_COUNT)

def neopixel_write(r, g, b):
    """设置 NeoPixel 的 RGB 亮度"""
    np[0] = (r, g, b)  # 设置第一个 NeoPixel 的颜色
    np.write()  # 发送数据更新

# 主循环
while True:
    # 尝试全亮红色
    neopixel_write(255, 0, 0)  # 红色全亮
    time.sleep(1)  # 延迟 1 秒

    # 尝试全亮绿色
    neopixel_write(0, 255, 0)  # 绿色全亮
    time.sleep(1)  # 延迟 1 秒

    # 尝试全亮蓝色
    neopixel_write(0, 0, 255)  # 蓝色全亮
    time.sleep(1)  # 延迟 1 秒

    # 关闭 LED
    neopixel_write(0, 0, 0)  # 关闭 LED
    time.sleep(1)  # 延迟 1 秒
