import socket

class hostB:
    def __init__(self):
        self.ip_port = ('127.0.0.1', 9999)  # 主机B的IP和端口
        self.sk_agent_hostB = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)  # 使用TCP连接
        self.sk_agent_hostB.bind(self.ip_port)
        self.sk_agent_hostB.listen(8)
        self.conn, self.addr = self.sk_agent_hostB.accept()  # 接收来自代理的数据

        self.MAX_SEQ = 7
        self.frame_expect = 0   # 需要接收的帧序号

    def checkError(self,dataStr):

        checksum = int(dataStr[-4:], 2) # 获取校验和
        ipt_str_accept = dataStr[:-4]

        b = ''.join([bin(ord(c))[2:] for c in ipt_str_accept])

        if len(b) % 4 != 0:
            l = 4 - len(b) % 4
            b = b + l * '0'

        b_array = []
        for i in range(0, len(b), 4):
            b_array.append(int(b[i:i + 4], 2))

        b_array_sum = sum(b_array)

        b_sum = 0

        while True:
            b_sum = 0

            shang = b_array_sum // 16
            yushu = b_array_sum % 16

            b_sum += yushu

            while shang > 0:
                b_array_sum = shang
                shang = b_array_sum // 16
                yushu = b_array_sum % 16

                b_sum += yushu

            if b_sum < 16:
                break
            else:
                b_array_sum = b_sum

        res_sum = b_sum + checksum

        res_sum = res_sum ^ 15  # 取反

        if res_sum == 0:
            return False    # 为0则没有出错
        else:
            return True

    # 求下一次接收的帧序号
    def addCircle(self, number):
        if (number < self.MAX_SEQ):
            return number + 1
        else:
            return 0

    def run(self):
        while True:
            data = str(self.conn.recv(1024),encoding="utf-8")  # 从agent处收到的数据
            if not self.checkError(data):   # 判断校验和是否正确
                if int(data[10]) == self.frame_expect:  # 判断是否为当前要接收的帧
                    print("从主机A收到的数据: ", data)
                    ack = str(self.frame_expect)
                    self.conn.sendall(bytes(ack, encoding="utf-8"))     #返回ack
                    self.frame_expect = self.addCircle(self.frame_expect)  # 计算下一次接收的帧序号
                else:
                    print(data)
            else:
                print("检验和出错！")

if __name__ == "__main__":
    hostB = hostB()
    hostB.run()