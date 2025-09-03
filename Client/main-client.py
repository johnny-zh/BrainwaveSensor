from machine import UART, Pin, I2S, unique_id
import network
import time
import usocket
import binascii
import urequests  # 用于 HTTP 请求
import gc  # 用于内存管理

# 定义EEG频段名称
EEG_BANDS = ["Delta", "Theta", "LowAlpha", "HighAlpha", "LowBeta", "HighBeta", "LowGamma", "MiddleGamma"]

# 初始化语音模块引脚
sck_pin = Pin(4)  # 串行时钟输出
ws_pin = Pin(5)   # 字时钟
sd_pin = Pin(3)   # 串行数据输出

# 初始化I2S音频输出
audio_out = I2S(1, sck=sck_pin, ws=ws_pin, sd=sd_pin, mode=I2S.TX, bits=16, format=I2S.MONO, rate=16000, ibuf=20000)

# 获取设备 ID
chip_id = binascii.hexlify(unique_id()).decode('utf-8')  # 获取芯片 ID 并转为十六进制字符串
print("ESP32 芯片 ID:", chip_id)

def play_audio(filename):
    """播放指定的WAV文件"""
    try:
        with open(filename, 'rb') as f:
            f.seek(44)  # 跳过WAV文件头44字节
            wav_samples = bytearray(1024)
            wav_samples_mv = memoryview(wav_samples)
            print(f"开始播放 {filename} ...")
            
            while True:
                num_read = f.readinto(wav_samples_mv)
                if num_read == 0:  # 文件结束
                    break
                num_written = 0
                while num_written < num_read:
                    num_written += audio_out.write(wav_samples_mv[num_written:num_read])
            print(f"{filename} 播放完成")
    except Exception as e:
        print(f"播放 {filename} 时发生错误: {e}")

def connect_wifi():
    """连接WiFi网络"""
    play_audio("1.wav")  # 阶段1：开机连接WiFi，播放语音1
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect('ZSZZ', 'zszz123456')
    
    timeout = 10
    start_time = time.time()
    
    while not wlan.isconnected():
        if time.time() - start_time > timeout:
            print("WiFi连接超时！")
            return False
        time.sleep(0.1)
    
    if wlan.isconnected():
        print("WiFi连接成功")
        print(f"IP地址：{wlan.ifconfig()[0]}")
        play_audio("2.wav")  # 阶段2：WiFi连接成功，播放语音2
        return True
    return False

def ping_server():
    """测试服务器是否可达"""
    try:
        sock = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('192.168.2.124', 9003))
        sock.close()
        print("服务器可达")
        return True
    except Exception as e:
        print(f"无法连接服务器: {e}")
        return False

def send_to_server(frame):
    """将二进制数据发送到服务器"""
    try:
        url = f"http://192.168.2.124:9003/api/device/eeg/NB001"
        headers = {'Content-Type': 'application/octet-stream'}
        print(f"发送请求到: {url}")
        print(f"数据长度: {len(frame)} 字节")
        print(f"数据内容: {' '.join('{:02X}'.format(b) for b in frame)}")
        
        # 释放内存，避免内存不足
        gc.collect()
        print(f"发送前可用内存: {gc.mem_free()} 字节")
        
        response = urequests.post(url, data=frame, headers=headers)
        print(f"服务器响应状态码: {response.status_code}")
        print(f"服务器响应内容: {response.text}")
        response.close()
        return True
    except Exception as e:
        print(f"发送数据到服务器失败: {e}")
        return False

def parse_frame(frame):
    """检查帧格式是否有效，返回0或1"""
    if len(frame) < 36 or frame[:4] != b'\xAA\xAA\x20\x02' or frame[31] != 0x04 or frame[33] != 0x05:
        return 0
    return 1

def main():
    # 配置UART1
    uart = UART(1, baudrate=57600, tx=Pin(1), rx=Pin(2))
    print("UART2 已初始化，等待数据...")
    
    # 连接WiFi
    if not connect_wifi():
        print("程序因WiFi连接失败而终止")
        return

    # 测试服务器连通性并记录状态
    server_reachable = ping_server()  # 初始检查服务器是否可达
    
    buffer = bytearray()
    start_sequence = b'\xAA\xAA\x20\x02'
    
    # 用于超时检测和状态管理
    last_valid_frame_time = time.time()  # 上次有效帧的时间
    last_reminder_time = 0  # 上次提醒的时间
    first_valid_frame_detected = False  # 标记是否检测到第一次有效帧
    audio_3_played = False  # 标记语音3是否已播放

    while True:
        data = uart.read()
        if data:
            print("串口数据:", ' '.join('{:02X}'.format(b) for b in data))
            buffer.extend(data)

            while len(buffer) >= 36:
                start_idx = buffer.find(start_sequence)
                if start_idx == -1:
                    buffer = buffer[-1:] if buffer else bytearray()
                    break

                if start_idx > 0:
                    buffer = buffer[start_idx:]

                if len(buffer) < 36:
                    break

                frame = buffer[:36]
                result = parse_frame(frame)

                if result:
                    print("\n有效帧检测: 1 (帧格式正确)")
                    current_time = time.time()
                    is_zero_frame = (frame[32] == 0x00 and frame[34] == 0x00)
                    
                    # 第一次有效帧的处理
                    if not first_valid_frame_detected:
                        if is_zero_frame:
                            play_audio("4.wav")  # 首次检测到零数据帧，播放语音4
                        else:
                            play_audio("3.wav")  # 首次检测到有效数据帧，播放语音3
                            audio_3_played = True  # 标记语音3已播放
                        first_valid_frame_detected = True
                    else:
                        # 后续帧的处理：如果之前没播放过语音3且当前帧有有效数据
                        if not audio_3_played and not is_zero_frame:
                            play_audio("3.wav")  # 从零数据恢复到有效数据，播放语音3
                            audio_3_played = True  # 标记语音3已播放
                    
                    # 判断服务器是否可达，只有可达时才发送数据
                    if server_reachable:
                        send_to_server(frame)
                    else:
                        print("服务器不可达，跳过数据发送")
                        
                    last_valid_frame_time = time.time()  # 更新上次有效帧时间
                else:
                    print("\n有效帧检测: 0 (帧格式错误)")

                buffer = buffer[36:]

        # 超时提醒逻辑（仅在第一次有效帧后启用）
        if first_valid_frame_detected:
            current_time = time.time()
            if current_time - last_valid_frame_time > 60: 
                if current_time - last_reminder_time >= 60:
                    play_audio("4.wav")  # 播放语音4
                    last_reminder_time = current_time

        time.sleep(0.01)

if __name__ == "__main__":
    main()

