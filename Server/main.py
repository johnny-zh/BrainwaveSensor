from machine import UART, Pin, I2S, unique_id, lightsleep
import network
import time
import usocket
import binascii
import gc
import ujson  # 用于JSON处理

# 定义EEG频段名称
EEG_BANDS = ["Delta", "Theta", "LowAlpha", "HighAlpha", "LowBeta", "HighBeta", "LowGamma", "MiddleGamma"]

# 初始化语音模块引脚
sck_pin = Pin(4)  # 串行时钟输出
ws_pin = Pin(5)   # 字时钟
sd_pin = Pin(3)   # 串行数据输出

# 初始化I2S音频输出
audio_out = I2S(1, sck=sck_pin, ws=ws_pin, sd=sd_pin, mode=I2S.TX, bits=16, format=I2S.MONO, rate=16000, ibuf=20000)

# 获取设备 ID
chip_id = binascii.hexlify(unique_id()).decode('utf-8')
print("ESP32 芯片 ID:", chip_id)

# 全局变量存储最新数据
latest_eeg_data = {"dataReady": 0, "Attention": 0, "Meditation": 0, "Alpha": 0, "Beta": 0, "Gamma": 0}

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
                if num_read == 0:
                    break
                num_written = 0
                while num_written < num_read:
                    num_written += audio_out.write(wav_samples_mv[num_written:num_read])
            print(f"{filename} 播放完成")
    except Exception as e:
        print(f"播放 {filename} 时发生错误: {e}")

def setup_ap():
    """配置ESP32为WiFi热点"""
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP32_EEG", password="12345678")  # 热点名称和密码
    while not ap.active():
        time.sleep(0.1)
    print("WiFi热点已开启")
    print("热点IP地址:", ap.ifconfig()[0])
    play_audio("2.wav")  # 热点开启成功，播放语音2
    return ap

def parse_frame(frame):
    """检查帧格式是否有效，返回0或1"""
    if len(frame) < 36 or frame[:4] != b'\xAA\xAA\x20\x02' or frame[31] != 0x04 or frame[33] != 0x05:
        return 0
    return 1

def update_eeg_data(frame):
    """解析frame[32]和frame[34]并更新全局数据"""
    global latest_eeg_data
    is_zero_frame = (frame[32] == 0x00 and frame[34] == 0x00)
    if is_zero_frame:
        latest_eeg_data = {"dataReady": 0, "Attention": 0, "Meditation": 0, "Alpha": 0, "Beta": 0, "Gamma": 0}
    else:
        attention = int(frame[32])  # 解析为十进制
        meditation = int(frame[34])  # 解析为十进制
        alpha = min(max(int(frame[17]), 0), 100)
        beta = min(max(int(frame[23]), 0), 100)
        gamma = min(max(int(frame[29]), 0), 100)
        latest_eeg_data = {"dataReady": 1, "Attention": attention, "Meditation": meditation, "Alpha": alpha, "Beta": beta, "Gamma": gamma}

def http_server():
    """简单的HTTP服务器，提供EEG数据接口"""
    addr = usocket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = usocket.socket()
    s.bind(addr)
    s.listen(1)
    print("HTTP服务器启动，监听端口80...")

    while True:
        try:
            cl, addr = s.accept()
            print("客户端连接来自:", addr)
            request = cl.recv(1024).decode('utf-8')
            
            # 简单解析GET请求
            if "GET /eeg_data" in request:
                response = ujson.dumps(latest_eeg_data)
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
                cl.send(response)
            else:
                cl.send("HTTP/1.1 404 Not Found\r\n\r\n")
                cl.send("404 - Not Found")
            
            cl.close()
        except Exception as e:
            print("HTTP服务器错误:", e)
            cl.close()

def main():
    play_audio("1-udp.wav")
    # 配置UART1
    uart = UART(1, baudrate=57600, tx=Pin(1), rx=Pin(2))
    print("UART1 已初始化，等待数据...")
    
    # 设置WiFi热点
    ap = setup_ap()
    
    # 启动HTTP服务器（在单独线程中运行，MicroPython中需手动模拟）
    import _thread
    _thread.start_new_thread(http_server, ())  # 在后台运行HTTP服务器
    
    buffer = bytearray()
    start_sequence = b'\xAA\xAA\x20\x02'
    
    # 用于超时检测和状态管理
    last_valid_frame_time = time.time()
    timeout_notification_sent = False
    frame_status_announced = False
    
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
                    is_zero_frame = (frame[32] == 0x00 and frame[34] == 0x00)
                    
                    # 更新EEG数据
                    update_eeg_data(frame)
                    
                    # 更新最后有效帧时间
                    last_valid_frame_time = time.time()
                    timeout_notification_sent = False
                    
                    # 只在首次检测到有效帧时播放语音
                    if not frame_status_announced:
                        if is_zero_frame:
                            play_audio("4.wav")
                        else:
                            play_audio("3.wav")
                        frame_status_announced = True
                else:
                    print("\n有效帧检测: 0 (帧格式错误)")

                buffer = buffer[36:]

        # 超时逻辑 - 仅在100秒无有效帧且未发送过通知时播放
        current_time = time.time()
        if (current_time - last_valid_frame_time > 100) and not timeout_notification_sent:
            play_audio("4.wav")
            timeout_notification_sent = True

        # 无数据时进入低功耗模式
        if not data:
            lightsleep(10)  # 休眠10ms，降低功耗
        else:
            time.sleep(0.01)  # 有数据时短暂延时

if __name__ == "__main__":
    main()

