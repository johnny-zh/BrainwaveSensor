import machine, time
from machine import Pin

BAUD_RATE = 115200

# 初始化 UART0，注意：有的设备 UART0 可能已用于 REPL，如有需要请更改为其他 UART 编号
uart = machine.UART(1, baudrate=BAUD_RATE, tx=Pin(1), rx=Pin(2))

# 发送初始化完成提示
uart.write("UART1\r\n")

last_time = time.ticks_ms()

while True:
    # 检查是否有接收到数据
    if uart.any():
        data_bytes = uart.read()  # 读取数据
        if data_bytes is not None:
            # 回显数据前先解码
            data = data_bytes.decode('utf-8')
            uart.write("received: " + data)
    
    # 每隔一秒发送一条消息
    if time.ticks_diff(time.ticks_ms(), last_time) > 1000:
        last_time = time.ticks_ms()
        uart.write("1111111111111111111\r\n")
