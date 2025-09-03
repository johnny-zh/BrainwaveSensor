from machine import UART, Pin
import time

# 使用 UART1 进行通信，避免干扰 REPL（UART0 默认用于 REPL）
# 请确保你的硬件连接正确，例如 TX 接在 GPIO21，RX 接在 GPIO20
uart = UART(1, baudrate=57600, tx=Pin(21), rx=Pin(20))

start_time = time.time()  # 记录开始时间
print("数据：")
while time.time() - start_time < 60:  # 循环运行 60 秒
    data = uart.read()  # 读取所有接收数据
    if data:
        # 以十六进制格式打印数据
        print(' '.join([f"{byte:02X}" for byte in data]))

print("一分钟的数据接收已结束")
