from pwsocket import WebSocket


ws = WebSocket('127.0.0.1', port=8080)
ws.onreceive = lambda ws, msg: ws.send('Server received: '+ msg + ', and Hello client!')
ws.accept()
try:
    while True:
        message =  ws.receive()
        print('received:', message)
        ws.send('Hello client!')
except WebSocket.ConnectionClosedError:
    print('Connection has been closed!')
except:
    pass # Other exceptions