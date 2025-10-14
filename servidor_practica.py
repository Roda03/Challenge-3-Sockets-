import socket
import threading

clientes_conectados = []

def manejar_clientes(cliente_socket, cliente_direccion):
    clientes_conectados.append(cliente_socket)
    # print(f"Conectado con: {cliente_direccion}")
    
    # Recibir el nombre del cliente
    nombre = cliente_socket.recv(1024).decode('utf-8')
    print(f"Nombre del cliente: {nombre}")
    
    # Enviar un saludo personalizado al cliente
    saludo = f"Hola, {nombre}, ¡bienvenido al servidor!"
    cliente_socket.send(saludo.encode('utf-8'))
    
    while True:
        try:
            mensaje_cliente = cliente_socket.recv(1024).decode('utf-8')
            
            if mensaje_cliente.lower() == "close":
                print(f"Cliente {cliente_direccion} desconectado.")
                break
            
            # Reenviar el mensaje a todos los demás clientes
            for cliente in clientes_conectados[:]:  # Usamos copia para evitar modificación durante iteración
                if cliente != cliente_socket:
                    try:
                        cliente.send(f"{nombre}: {mensaje_cliente}".encode('utf-8'))
                    except:
                        clientes_conectados.remove(cliente)
            
            print(f"{nombre}: {mensaje_cliente}")
            
            # NO enviar confirmación aquí - esto causa el bloqueo
            
        except Exception as e:
            print(f"Error con cliente {nombre}: {e}")
            break
            
    if cliente_socket in clientes_conectados:
        clientes_conectados.remove(cliente_socket)
    cliente_socket.close()

def abrir_servidor():
    servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    ip_servidor = "127.0.0.1"
    puerto_servidor = 8000
    
    servidor_socket.bind((ip_servidor, puerto_servidor))
    servidor_socket.listen(5)
    print(f"Servidor escuchando en {ip_servidor}:{puerto_servidor}")
    
    while True:
        cliente_socket, direccion_cliente = servidor_socket.accept()
        hilo_cliente = threading.Thread(target=manejar_clientes, args=(cliente_socket, direccion_cliente))
        hilo_cliente.start()

abrir_servidor()