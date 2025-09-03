from machine import UART, Pin
import time

# 定义EEG频段名称
EEG_BANDS = ["Delta", "Theta", "LowAlpha", "HighAlpha", "LowBeta", "HighBeta", "LowGamma", "MiddleGamma"]

def calculate_eeg_power(data):
    """计算EEG功率值，每组3字节转换为一个整数"""
    powers = []
    for i in range(0, 24, 3):  # 从索引0到23，每3字节一组，共8组
        high = data[i]
        mid = data[i + 1]
        low = data[i + 2]
        value = (high << 16) | (mid << 8) | low  # 高字节左移16位，中字节左移8位，低字节不变
        powers.append(value)
    return powers

def parse_frame(frame):
    """解析帧数据，检测第31字节=04和第33字节=05，跳过校验和"""
    try:
        # 检查最小长度和关键标识
        if len(frame) < 35 or frame[:4] != b'\xAA\xAA\x20\x02' or frame[31] != 0x04 or frame[33] != 0x05:
            return None

        # 提取EEG功率部分（字节7-30，共24字节）
        eeg_data = frame[7:31]
        eeg_powers = calculate_eeg_power(eeg_data)

        # 提取注意力值（字节31-32）
        attention = frame[32]

        # 提取冥想值（字节33-34）
        meditation = frame[34]

        return eeg_powers, attention, meditation
    except Exception:
        return None

def main():
    # wroom 配置UART2，波特率57600，TX=17，RX=16 
    #uart = UART(2, baudrate=57600, tx=Pin(17), rx=Pin(16))
    #print("UART2 已初始化，等待数据...")
    # wroom 配置UART2，波特率57600，TX=17，RX=16 
    uart = UART(1, baudrate=57600, tx=Pin(1), rx=Pin(2))
    print("UART1 已初始化，等待数据...")

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
                    eeg_powers, attention, meditation = result
                    # 输出有效帧的解析结果
                    print("\n有效数据:", ' '.join('{:02X}'.format(b) for b in frame))
                    print("EEG功率值:")
                    for band, power in zip(EEG_BANDS, eeg_powers):
                        print(f"{band}: {power}")
                    print(f"专注度: {attention}")
                    print(f"放松度: {meditation}")

                # 删除已处理的帧（35字节，包括校验和）
                buffer = buffer[35:]

        time.sleep(0.01)  # 短暂休眠，避免CPU占用过高

if __name__ == "__main__":
    main()

