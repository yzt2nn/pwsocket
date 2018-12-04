# pwsocket
## pwsocket是一个包含最简websocket连接及通信需要的python用连接器。
## 它包括以下几个特点:
* 轻便小巧，使用简单
* 使用封装起来的websocket对象进行操作
## 使用方法:
1. 导入pwsocket
```python
from your_file_position.pwsocket import WebSocket
```
2. 创建连接对象
```python
ws = WebSocket('127.0.0.1', port=8080)
```
WebScoket类在构造时可传入以下参数:
```python
WebSocket(host, port=80, bufsize=4096, timeout=0, conn_timeout=0)
```
* host 主机的ip地址，若是'0.0.0.0'则不限定地址，通常用于主机有多个ip时。
* port 监听的端口号，请尽量选择通常不会被占用的端口。
* bufsize 单次接收消息的最大字节数，若该参数小于客户端发来的消息包的总大小，会造成消息不完整，以至于解析异常
* timeout 接收消息的最长等待时间，超时后会抛出socket.timeout异常，此异常在pwsocket中未作处理
* conn_timeout 连接最长等待时间，超出该时间，则监听关闭。
3. 监听客户端连接，该步骤会阻塞直到超时或连接成功
```python
ws.accept()
```
4. 还可以定义receive的回调函数，在每次接收消息成功后自动执行(如不需要可以跳过此步)。
```python
ws.onreceive = lambda ws, msg: ws.send('Server received: '+ msg + ', and Hello client!')
```
5. 收发消息
```python
try:
    while True:
        message =  ws.receive()
        print('received:', message)
        ws.send('Hello client!')
except WebSocket.ConnectionClosedError:
    # 调用接收和发送函数时，如果连接已经关闭，会抛出ConnectionClosedError异常
    print('Connection has been closed!')
except:
    pass # Other exceptions
```
## 注意
pwsocket尚未支持多帧消息的接收，即消息帧FIN位为0的情况。