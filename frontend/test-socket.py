import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('127.0.0.1', 3000))
s.listen(5)
print("Server listening on 127.0.0.1:3000")
while True:
    conn, addr = s.accept()
    print(f"Connection from {addr}")
    conn.send(b"HTTP/1.1 200 OK\r\nContent-Length: 11\r\n\r\nHello World")
    conn.close()