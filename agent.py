import socket
import threading
import random
import time

class agent:
    def __init__(self):
        self.ip_port = ('127.0.0.1', 9998)  # 自己的IP和端口
        self.sk_hostA_agent = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.sk_hostA_agent.bind(self.ip_port)
        self.sk_hostA_agent.listen(8)
        self.conn, self.addr = self.sk_hostA_agent.accept()  # 接收来自主机A的数据

        self.ip_port2 = ('127.0.0.1', 9999)  # 连接到主机B的IP和端口
        self.sk_agent_hostB = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.sk_agent_hostB.connect(self.ip_port2)  # 连接代理（传输模拟器）

        self.delayQueue = []    # 用于保存延迟帧的队列
        self.delayTime = 0      # 延迟时间

    # 从主机B中获取数据
    def B_to_A(self):
        while True:
            hostB_ack = self.sk_agent_hostB.recv(1024)  # 收到主机B的ack后转发给主机A
            if hostB_ack:
                self.conn.sendall(hostB_ack)

        self.sk_agent_hostB.close()

    # 从主机A中获取数据
    def A_to_B(self):
        while True:
            data = self.conn.recv(1024)
            if data:
                self.sk_agent_hostB.sendall(data)

        self.conn.close()

    # 模拟丢包函数，丢包率为10%
    def discardPackets(self):
        while True:

            data = self.conn.recv(1024)

            if data:
                rate = random.random()
                if rate < 0.9:
                    self.sk_agent_hostB.sendall(data)
                else:
                    print("丢弃帧：",str(data,encoding="UTF-8"))

        self.conn.close()

    # 模拟出错函数
    def simuError(self):
        while True:

            data = self.conn.recv(1024)

            if data:
                rate = random.random()

                if rate < 0.1:  # 以1%的概率出错
                    data = str(data,encoding="UTF-8")
                    source_data = data
                    pos = random.randint(0, 10)  # 随机选择一个字符串位置出错
                    index = random.randint(97, 122)  # 随机选择一个替换的字符
                    char = chr(index)  # 转换为字符
                    data = data.replace(data[pos], char, 1)  # 替换字符
                    data = bytes(data,encoding="UTF-8")

                    print("出错帧：从原始帧",source_data,"变为出错帧",str(data,encoding="UTF-8"))
                self.sk_agent_hostB.sendall(data)

        self.conn.close()

    # 模拟延迟函数
    def simuDelay(self):
        while True:
            data = self.conn.recv(1024)
            if data:
                rate = random.random()
                if rate < 0.1:  # 20%的概率产生延迟
                    print("帧延迟：",str(data,encoding="UTF-8"))
                    self.delayQueue.append(data)    # 放入延迟队列
                else:
                    self.sk_agent_hostB.sendall(data)
                    if len(self.delayQueue) > 0:
                        self.delayTime += 1 # 延迟计时
            if self.delayTime > 2:  # 延迟两个帧再发送
                reTransData = self.delayQueue.pop()
                self.delayQueue.clear() # 清除延迟队列
                self.delayTime = 0  # 重置延迟计时
                self.sk_agent_hostB.sendall(reTransData)

        self.conn.close()

    # 入口函数
    def run(self,control):
        if control == 0: # 正常执行
            AtoB = threading.Thread(target=self.A_to_B)
            AtoB.start()

            BtoA = threading.Thread(target=self.B_to_A)
            BtoA.start()

        elif control == 1:    # 模拟丢包错误
            AtoB = threading.Thread(target=self.discardPackets)
            AtoB.start()

            BtoA = threading.Thread(target=self.B_to_A)
            BtoA.start()

        elif control == 2:  # 模拟数据出错
            AtoB = threading.Thread(target=self.simuError)
            AtoB.start()

            BtoA = threading.Thread(target=self.B_to_A)
            BtoA.start()

        elif control == 3:  # 模拟延迟
            AtoB = threading.Thread(target=self.simuDelay)
            AtoB.start()

            BtoA = threading.Thread(target=self.B_to_A)
            BtoA.start()

if __name__ == "__main__":
    agent = agent()
    agent.run(1)

