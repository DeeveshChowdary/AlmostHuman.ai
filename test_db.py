import socket
try:
    print(socket.getaddrinfo('db.fauddzuzrwqdovqrszcu.supabase.co', 5432))
except Exception as e:
    print("DNS FAIL:", e)
