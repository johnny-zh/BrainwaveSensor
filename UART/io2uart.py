from machine import Pin
import time

TX_PIN = Pin(0, Pin.OUT)
BAUD_RATE = 9600  # 进一步降低
BIT_TIME = int(1000000 / BAUD_RATE)

def soft_uart_write(byte_data):
    TX_PIN.value(1)
    TX_PIN.value(0)  # 起始位
    time.sleep_us(BIT_TIME)
    for i in range(8):
        bit = (byte_data >> i) & 1
        TX_PIN.value(bit)
        time.sleep_us(BIT_TIME)
    TX_PIN.value(1)  # 停止位
    time.sleep_us(BIT_TIME)

def send_binary(data):
    for byte in data:
        soft_uart_write(byte)

print("开始发送...")
start_time = time.time()
test_data = b'AB'  # 只发送 0x41
while time.time() - start_time < 60:
    send_binary(test_data)
    time.sleep(0.5)
print("发送完成")
