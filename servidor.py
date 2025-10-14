import socket             # biblioteca base para crear sockets TCP
import threading          # permite manejar múltiples clientes a la vez usando hilos

clientes_conectados = []  # lista global con los sockets de todos los clientes conectados

def manejar_clientes(cliente_socket, cliente_direccion):
    clientes_conectados.append(cliente_socket)  # registramos el nuevo cliente en la lista activa
    try:
        nombre = cliente_socket.recv(1024).decode('utf-8')  # handshake simple: el cliente envía su nombre
        print(f"Nombre del cliente: {nombre}")              # log informativo en el servidor
        cliente_socket.send(f"Hola, {nombre}, ¡bienvenido al servidor!".encode('utf-8'))  # saludo inicial

        while True:  # bucle principal de atención a este cliente
            try:
                data = cliente_socket.recv(1024)  # leer bytes del socket del cliente

                # ⬇️ CASO 1: el cliente cerró la conexión ordenadamente → recv() retorna b''
                if not data:
                    print(f"📤 {nombre} se desconectó (cierre de socket)")  # log de salida por cierre normal
                    # avisar a los demás clientes que este usuario salió
                    for c in clientes_conectados[:]:  # iteramos sobre una copia para poder remover seguros
                        if c is not cliente_socket:
                            try:
                                c.send(f"📤 {nombre} salió del chat".encode('utf-8'))  # broadcast de salida
                            except:
                                try: c.close(); clientes_conectados.remove(c)
                                except: pass
                    break  # salimos del bucle de este cliente

                mensaje_cliente = data.decode('utf-8').strip()  # decodificamos y limpiamos \r\n y espacios
                if not mensaje_cliente:
                    continue  # descartamos líneas vacías para evitar imprimir "nombre:" sin contenido

                # si el cliente envía la palabra clave de cierre, registramos y salimos
                if mensaje_cliente.lower() == "close":
                    print(f"📤 {nombre} se desconectó (close)")  # log de salida voluntaria
                    # avisar a los demás clientes que este usuario salió
                    for c in clientes_conectados[:]:
                        if c is not cliente_socket:
                            try:
                                c.send(f"📤 {nombre} salió del chat".encode('utf-8'))  # broadcast de salida
                            except:
                                try: c.close(); clientes_conectados.remove(c)
                                except: pass
                    break  # salimos del bucle de este cliente

                # reenviamos el mensaje a todos menos al emisor para lograr el efecto broadcast
                for c in clientes_conectados[:]:
                    if c is not cliente_socket:
                        try:
                            c.send(f"{nombre}: {mensaje_cliente}".encode('utf-8'))  # formato nombre: mensaje
                        except:
                            # si un envío falla, cerramos y limpiamos ese socket de la lista activa
                            try: c.close(); clientes_conectados.remove(c)
                            except: pass

                print(f"{nombre}: {mensaje_cliente}")  # log del mensaje recibido en la consola del servidor

            # ⬇️ CASO 2: corte brusco de la conexión por parte del cliente
            except ConnectionResetError:
                print(f"⚠️ {nombre} se desconectó abruptamente (reset)")  # conexión reseteada por el peer
                break
            except Exception as e:
                print(f"Error con cliente {nombre}: {e}")  # cualquier otro error en el manejo de este cliente
                break
    finally:
        # limpieza final: remover el socket del cliente de la lista y cerrarlo
        if cliente_socket in clientes_conectados:
            clientes_conectados.remove(cliente_socket)  # mantenemos la lista de clientes consistente
        try: cliente_socket.close()  # liberamos el recurso del socket del cliente
        except: pass


def abrir_servidor():  # configura y arranca el servidor TCP
    servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket IPv4 + TCP
    
    ip_servidor = "127.0.0.1"  # dirección IP donde escuchará el servidor
    puerto_servidor = 8000     # puerto TCP de escucha
    
    servidor_socket.bind((ip_servidor, puerto_servidor))  # liga IP y puerto al socket del servidor
    servidor_socket.listen(5)                             # pone el socket en modo escucha con backlog de 5
    print(f"Servidor escuchando en {ip_servidor}:{puerto_servidor}")  # mensaje informativo de arranque
    
    while True:  # bucle de aceptación de nuevos clientes
        cliente_socket, direccion_cliente = servidor_socket.accept()  # bloqueo hasta que llegue una conexión
        # creamos un hilo dedicado para atender a este nuevo cliente sin bloquear a los demás
        hilo_cliente = threading.Thread(
            target=manejar_clientes,                # función que gestionará al cliente
            args=(cliente_socket, direccion_cliente)  # pasamos el socket y la dirección del cliente
        )
        hilo_cliente.start()  # iniciamos el hilo para atención concurrente

abrir_servidor()  # punto de entrada del servidor
