from machine import UART, Pin, I2S, unique_id
import network
import time
import usocket
import binascii
import gc
import ujson
import neopixel

# 定义EEG频段名称
EEG_BANDS = ["Delta", "Theta", "LowAlpha", "HighAlpha", "LowBeta", "HighBeta", "LowGamma", "MiddleGamma"]

# 初始化语音模块引脚
sck_pin = Pin(4)
ws_pin = Pin(5)
sd_pin = Pin(3)

# 初始化I2S音频输出
audio_out = I2S(1, sck=sck_pin, ws=ws_pin, sd=sd_pin, mode=I2S.TX, bits=16, format=I2S.MONO, rate=16000, ibuf=20000)

# 获取设备 ID
chip_id = binascii.hexlify(unique_id()).decode('utf-8')
print("ESP32 芯片 ID:", chip_id)

# 定义 NeoPixel 引脚和数量
RGB_BUILTIN_PIN = 21  # 数据引脚，确保连接正确
RGB_BUILTIN_COUNT = 1  # 只有一个 NeoPixel

# 初始化 NeoPixel
np = neopixel.NeoPixel(Pin(RGB_BUILTIN_PIN), RGB_BUILTIN_COUNT)

def neopixel_write(r, g, b):
    """设置 NeoPixel 的 RGB 亮度"""
    np[0] = (r, g, b)  # 设置第一个 NeoPixel 的颜色
    np.write()  # 发送数据更新

# 全局变量，用于存储最新的EEG数据
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
    play_audio("1-udp.wav")  # 阶段1：开机连接WiFi，播放语音1
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect('JSZN', 'jszn666666')
    
    timeout = 10
    start_time = time.time()
    
    while not wlan.isconnected():
        if time.time() - start_time > timeout:
            print("WiFi连接超时！")
            neopixel_write(0, 255, 0)  # WiFi连接失败，常亮红灯
            return False
        time.sleep(0.1)
    
    if wlan.isconnected():
        print("WiFi连接成功")
        print(f"IP地址：{wlan.ifconfig()[0]}")
        play_audio("2.wav")  # 阶段2：WiFi连接成功，播放语音2
        neopixel_write(0, 0, 255)  # WiFi连接成功，常亮蓝灯
        return True
    return False

def update_eeg_data(frame):
    """解析frame[18]、frame[24]、frame[30]、frame[32]和frame[34]并更新全局数据"""
    global latest_eeg_data
    is_zero_frame = (frame[32] == 0x00 and frame[34] == 0x00)
    if is_zero_frame:
        latest_eeg_data = {"dataReady": 0, "Attention": 0, "Meditation": 0, "Alpha": 0, "Beta": 0, "Gamma": 0}
    else:
        attention = int(frame[32])
        meditation = int(frame[34])
        alpha = min(max(int(frame[17]), 0), 100)
        beta = min(max(int(frame[23]), 0), 100)
        gamma = min(max(int(frame[29]), 0), 100)

        latest_eeg_data = {
            "dataReady": 1,
            "Attention": attention,
            "Meditation": meditation,
            "Alpha": alpha,
            "Beta": beta,
            "Gamma": gamma
        }

def broadcast_udp_json():
    """通过UDP广播将JSON格式的EEG数据发送到局域网内的所有设备"""
    try:
        sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)
        sock.setsockopt(usocket.SOL_SOCKET, usocket.SO_BROADCAST, 1)
        broadcast_addr = ("255.255.255.255", 9003)
        json_data = ujson.dumps(latest_eeg_data).encode('utf-8')
        
        print(f"UDP广播JSON数据到 {broadcast_addr}")
        print(f"JSON数据: {json_data.decode('utf-8')}")
        print(f"数据长度: {len(json_data)} 字节")
        
        gc.collect()
        print(f"发送前可用内存: {gc.mem_free()} 字节")
        
        sock.sendto(json_data, broadcast_addr)
        sock.close()
        print("UDP JSON广播发送成功")
        neopixel_write(0, 0, 255)  # 数据上传成功，常亮蓝灯
        return True
    except Exception as e:
        print(f"UDP JSON广播发送失败: {e}")
        # 数据上传失败，闪烁红灯
        for _ in range(2):  # 闪烁两次
            neopixel_write(0, 255, 0)  # 红灯亮
            time.sleep(0.5)
            neopixel_write(0, 0, 0)  # 红灯灭
            time.sleep(0.5)
        return False

def parse_frame(frame):
    """检查帧格式是否有效，返回0或1"""
    if len(frame) < 36 or frame[:4] != b'\xAA\xAA\x20\x02' or frame[31] != 0x04 or frame[33] != 0x05:
        return 0
    return 1

def main():
    # 通电后常亮蓝灯
    neopixel_write(0, 0, 255)
    
    # 配置UART1
    uart = UART(1, baudrate=57600, tx=Pin(1), rx=Pin(2))
    print("UART2 已初始化，等待数据...")
    
    # 连接WiFi
    if not connect_wifi():
        print("程序因WiFi连接失败而终止")
        return
    
    buffer = bytearray()
    start_sequence = b'\xAA\xAA\x20\x02'
    
    # 状态管理
    last_valid_frame_time = time.time()
    last_reminder_time = 0
    frame_status_played = False  # 是否已经播放了帧状态语音
    
    while True:
        data = uart.read()
        if data:
            print("串口数据:", ' '.join('{:02X}'.format(b) for b in data))
            buffer.extend(data)

            while len(buffer) >= 36:
                start_idx = buffer.find(start_sequence)
                if start_idx == -1:
                    buffer = buffer[-3:] if len(buffer) > 3 else buffer  # 保留最后3个字节以防分割序列
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
                    
                    # 只在首次判断帧状态时播放语音
                    if not frame_status_played:
                        if is_zero_frame:
                            play_audio("4.wav")  # 零帧播放语音4
                        else:
                            play_audio("3.wav")  # 非零帧播放语音3
                        frame_status_played = True
                    
                    broadcast_udp_json()
                    last_valid_frame_time = time.time()
                else:
                    print("\n有效帧检测: 0 (帧格式错误)")
                    # 帧格式错误，闪烁红灯
                    for _ in range(2):  # 闪烁两次
                        neopixel_write(0, 255, 0)  # 红灯亮
                        time.sleep(0.5)
                        neopixel_write(0, 255, 0)  # 红灯灭
                        time.sleep(0.5)
                    neopixel_write(0, 255, 0)  # 恢复蓝灯

                buffer = buffer[36:]

        # 超时逻辑：超过100秒没有有效帧时，播放语音4并闪烁红灯
        current_time = time.time()
        if current_time - last_valid_frame_time > 100:  # 100秒超时
            if current_time - last_reminder_time >= 100:  # 每100秒提醒一次
                play_audio("4.wav")
                # 闪烁红灯
                for _ in range(2):  # 闪烁两次
                    neopixel_write(255, 0, 0)  # 红灯亮
                    time.sleep(0.5)
                    neopixel_write(0, 0, 0)  # 红灯灭
                    time.sleep(0.5)
                neopixel_write(0, 0, 255)  # 恢复蓝灯
                last_reminder_time = current_time

        time.sleep(0.01)

if __name__ == "__main__":
    main()

