import socket
import threading
import time

lock = threading.Lock() #互斥锁

class hostA:
    def __init__(self):
        self.selfIP_Port = ('127.0.0.1', 9997)  # 主机A的IP端口

        self.sendIP_Port = ('127.0.0.1', 9998)  # 代理的IP和端口
        self.sk_hostA_agent = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)  # 使用TCP进行数据发送
        self.sk_hostA_agent.connect(self.sendIP_Port)  # 连接代理（传输模拟器）

        self.MAX_SEQ = 7  # 窗口大小
        self.timeout_limit = 5  # 定时器超时限制
        self.timeout_ack = None  # 保存超时的帧在send_buffer中的索引
        self.send_buffer = ["0000+0000+8" for i in range(self.MAX_SEQ+1)]  # 发送端的缓冲区，最大为7
        self.nbuffered = 0  # 缓冲区中的数据报数量
        self.ack_expect = 0  # 保存从接收端收到的ack信息
        self.frame_to_send = 0  # 保存当前或下一次要发送的帧号
        self.event = "allow_send"  # 用于记录当前的时间（超时，校验和错误，能否发送数据）
        self.timer_list = ["" for i in range(self.MAX_SEQ + 1)]  # 用于保存发送的每个帧的定时器
        self.send_successful = 0    # 记录发送成功的帧数

        self.send_end = False

    # 为ack创建定时器
    # 时间从0开始递增
    def start_ack_timer(self,ack,start=0):
        if start >= self.timeout_limit:     # 检测到超时
            self.event = "timeout"         # 将事件设置为event

            self.timeout_ack = ack          # 保存当前超时的帧

            for timer in self.timer_list:   # 关闭所有定时器
                if timer != "":
                    timer.cancel()

            return
        else:
            start += 1
            self.timer_list[ack] = threading.Timer(1, self.start_ack_timer, (ack,start))
            self.timer_list[ack].start()

    # 停止ack的计时器
    def stop_ack_timer(self,ack):
        #print("time end: ",ack)
        self.timer_list[ack].cancel()

    # 通过ack获取数据在缓冲数组中的索引
    def getBufferIndexByAck(self,ack):
        for i in range(self.MAX_SEQ):
            if int(self.send_buffer[i][10])==ack:
                return i
        return -1

    # 求下一次发送的帧序号
    def addCircle(self,number):
        if(number < self.MAX_SEQ):
            return number+1
        else:
            return 0

    # 添加校验和函数
    # 划分位4位一段，求校验和
    def addChecksum(self,dataStr):
        # 如果长度不是4的倍数，则在末尾添0
        binStr = ''.join([bin(ord(c))[2:] for c in dataStr])    # 将数据转为二进制

        if len(binStr) % 4 != 0:    # 如果长度不是4的整数倍，则填零到4的倍数
            l = 4 - len(binStr) % 4
            binStr = binStr + l * '0'

        # 每四位划分为一个数，转为整数，相加得到和
        a_array = []
        for i in range(0, len(binStr), 4):
            a_array.append(int(binStr[i:i + 4], 2))

        array_sum = sum(a_array)    # 求和

        checksum = 0    # 校验和

        while True: # 循环求取校验和
            checksum = 0

            shang = array_sum // 16 # 商
            yushu = array_sum % 16  # 余数

            checksum += yushu   # 将每一次的余数加到当前校验和中

            while shang > 0:    # 当商大于0时继续
                array_sum = shang
                shang = array_sum // 16
                yushu = array_sum % 16

                checksum += yushu

            if checksum < 16:   # 若小于16则说明位数小于等于4位，停止计算，否则将高位折回继续求和
                break
            else:
                array_sum = checksum

        checksum = bin(checksum ^ 15)[2:]  # 取反，并转化为二进制
        if len(checksum) != 4:
            checksum = (4 - len(checksum))*'0'+checksum

        return dataStr + checksum   # 返回添加了校验和的数据

    def sendData(self):

        send_data = input('请输入要传送的数据（exit退出）：').strip()  # 输入要传输的数据
        send_pointer = 0  # 初始化数据传输位置指针

        while send_data != "exit":
            # 输入要传输的数据
            if self.send_successful >= len(send_data):
                print("数据传输完成!")
                self.send_successful = 0
                send_pointer = 0  # 初始化数据传输位置指针
                send_data = input('请重新输入要传送的数据（exit退出）：').strip()  # 输入要传输的数据
                # if send_data == "exit":
                #     break

            if self.event == "allow_send" and send_pointer<len(send_data):  # 若允许传输数据
                frame = "9999+9997+" + str(self.frame_to_send) + "+" + send_data[send_pointer]  # 封装帧格式
                frame = self.addChecksum(frame)
                self.send_buffer[self.frame_to_send] = frame  # 保存当前发送帧到缓冲数组
                lock.acquire()  # 多线程互斥访问
                self.nbuffered += 1  # 发送缓冲填充数据增1
                lock.release()
                send_pointer += 1  # 数据位置指针增1

                time.sleep(0.5)
                timer = threading.Timer(1, self.start_ack_timer, (self.frame_to_send, 0))  # 开启定时器
                self.timer_list[self.frame_to_send] = timer  # 将当前定时器添加到定时器列表
                self.timer_list[self.frame_to_send].start()

                self.sk_hostA_agent.sendall(bytes(frame, encoding="utf-8"))  # 发送帧
                print("发送帧：", frame)

                self.frame_to_send = self.addCircle(self.frame_to_send)  # 计算下一次发送的帧序号

            elif self.event == "timeout":  # 超时情况
                #index = self.getBufferIndexByAck(self.timeout_ack)  # 获取超时的ack对应的索引(既帧序号)
                print("检测到超时帧：", self.timeout_ack)
                self.frame_to_send = self.timeout_ack
                for i in range(self.nbuffered):
                    print("重发帧：", self.send_buffer[self.frame_to_send])
                    time.sleep(0.5)

                    timer = threading.Timer(1, self.start_ack_timer, (self.frame_to_send, 0))  # 开启定时器
                    self.timer_list[self.frame_to_send] = timer  # 将当前定时器添加到定时器列表
                    self.timer_list[self.frame_to_send].start()

                    self.sk_hostA_agent.sendall(bytes(self.send_buffer[self.frame_to_send], encoding="utf-8"))  # 发送帧
                    self.frame_to_send = self.addCircle(self.frame_to_send)  # 计算下一次发送的帧序号

                self.event = "allow_send"

            if self.nbuffered >= self.MAX_SEQ:
                self.event = "disable_send"  # 一次只能发送7个窗口大小的数据

        self.send_end = True
        #self.sk_hostA_agent.close()  # 传输完成后，断开连接

    def getAckData(self):
        while not self.send_end:
            ack = int(str(self.sk_hostA_agent.recv(1024), encoding="utf-8"))  # 收到主机B的ack后转发给主机A
            if ack >= 0 and ack<=7:
                self.timer_list[ack].cancel()  # 停止掉ack的定时器
                if ack == self.ack_expect:
                    self.send_successful += 1
                    lock.acquire()  # 互斥访问
                    self.nbuffered -= 1
                    lock.release()
                    self.ack_expect = (self.ack_expect + 1) % (self.MAX_SEQ + 1)
                    self.timer_list[ack].cancel()
        self.sk_hostA_agent.close()  # 传输完成后，断开连接

    def run(self):

        sendDataThread = threading.Thread(target=self.sendData)
        sendDataThread.start()

        getAckThread = threading.Thread(target=self.getAckData)
        getAckThread.start()
        
       # self.sendData()

if __name__ == "__main__":
    hostA = hostA()
    hostA.run()