import network
import time

# 初始化WiFi连接
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# 连接WiFi
wlan.connect('JSZN', 'jszn666666')

# 等待WiFi连接成功
timeout = 10  # 设置超时时间（10秒）
start_time = time.time()

while not wlan.isconnected():
    if time.time() - start_time > timeout:
        print("WiFi连接超时！")
        break
    time.sleep(0.1)

# 如果连接成功，打印IP地址
if wlan.isconnected():
    print("WiFi连接成功")
    print(f"IP地址：{wlan.ifconfig()[0]}")
