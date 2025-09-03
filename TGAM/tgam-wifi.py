from machine import UART, Pin
import network
import time
import usocket  # 使用socket进行网络通信

# 定义EEG频段名称
EEG_BANDS = ["Delta", "Theta", "LowAlpha", "HighAlpha", "LowBeta", "HighBeta", "LowGamma", "MiddleGamma"]

def connect_wifi():
    """连接WiFi网络"""
    wlan = network.WLAN(network.STA_IF)
    
    # 重置 WiFi 模块
    wlan.active(False)
    time.sleep(1)
    wlan.active(True)
    print("WiFi 模块已激活")
    
    # 扫描网络
    print("扫描网络...")
    networks = wlan.scan()
    for net in networks:
        print(f"SSID: {net[0].decode()}, RSSI: {net[3]}")
    
    # 连接 WiFi
    ssid = 'JSZN'
    password = 'jszn666666'
    print(f"连接 SSID: {ssid}, 密码: {password}")
    wlan.connect(ssid, password)
    
    timeout = 20
    start_time = time.time()
    
    while not wlan.isconnected():
        status = wlan.status()
        if time.time() - start_time > timeout:
            print("WiFi连接超时！")
            print(f"最终状态: {status}")
            return False
        print(f"当前状态: {status}")
        time.sleep(0.5)
    
    print("WiFi连接成功")
    print(f"IP地址: {wlan.ifconfig()[0]}")
    return True



def send_to_server(frame):
    """将二进制数据发送到服务器"""
    try:
        # 创建socket连接
        sock = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        
        # 服务器地址和端口（需要根据你的服务器配置修改）
        server_address = ('192.168.2.200', 12345)  # 示例IP和端口，请替换为实际服务器地址
        sock.connect(server_address)
        
        # 发送二进制数据
        sock.sendall(frame)
        print("数据已发送到服务器")
        
        # 关闭socket
        sock.close()
        return True
    except Exception as e:
        print(f"发送数据到服务器失败: {e}")
        return False

def parse_frame(frame):
    """检查帧格式是否有效，返回0或1"""
    if len(frame) < 35 or frame[:4] != b'\xAA\xAA\x20\x02' or frame[31] != 0x04 or frame[33] != 0x05:
        return 0
    return 1

def main():
    # 配置UART2，波特率57600，TX=17，RX=16
    uart = UART(2, baudrate=57600, tx=Pin(17), rx=Pin(16))
    print("UART2 已初始化，等待数据...")
    
    # 连接WiFi
    if not connect_wifi():
        print("程序因WiFi连接失败而终止")
        return
    
    buffer = bytearray()  # 数据缓冲区
    start_sequence = b'\xAA\xAA\x20\x02'  # 帧起始标记

    while True:
        # 读取UART2数据
        data = uart.read()  # 读取所有可用数据
        if data:
            # 打印串口读取到的所有数据
            print("串口数据:", ' '.join('{:02X}'.format(b) for b in data))
            buffer.extend(data)

            # 查找并解析帧
            while len(buffer) >= 35:  # 至少需要35字节（包括校验和）
                start_idx = buffer.find(start_sequence)
                if start_idx == -1:
                    buffer = buffer[-1:] if buffer else bytearray()
                    break

                # 如果起始标记不在缓冲区开头，移除之前的数据
                if start_idx > 0:
                    buffer = buffer[start_idx:]

                # 检查是否足够长度解析完整帧
                if len(buffer) < 35:
                    break

                # 提取35字节的帧（包括校验和）
                frame = buffer[:35]
                result = parse_frame(frame)

                if result:
                    print("\n有效帧检测: 1 (帧格式正确)")
                    # 如果帧有效，发送到服务器
                    send_to_server(frame)
                else:
                    print("\n有效帧检测: 0 (帧格式错误)")

                # 删除已处理的帧（35字节，包括校验和）
                buffer = buffer[35:]

        time.sleep(0.01)  # 短暂休眠，避免CPU占用过高

if __name__ == "__main__":
    main()
