import socket
import threading
import sys

def recibir_mensajes(cliente_socket, mi_nombre):
    while True:
        try:
            mensaje = cliente_socket.recv(1024).decode('utf-8')
            if mensaje:
                # Insertar el mensaje recibido encima del input actual
                sys.stdout.write('\r')  # Ir al inicio de línea
                
                # Crear espacio para el nuevo mensaje manteniendo el input actual
                if ":" in mensaje and not mensaje.startswith(mi_nombre + ":"):
                    sys.stdout.write(f'\n👤 {mensaje}\n')
                else:
                    sys.stdout.write(f'\n📢 {mensaje}\n')
                
                # El input actual se mantiene visible y editable
                sys.stdout.write('Tu mensaje: ')
                sys.stdout.flush()
                
            else:
                break
        except Exception as e:
            print(f"Error:{e}")
            break

def empezar_cliente():
    cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    ip_cliente = "127.0.0.1"
    puerto = 8000
    
    try:
        cliente_socket.connect((ip_cliente, puerto))
        print(f"Conectado al servidor en {ip_cliente}:{puerto}")
        
        nombre_cliente = input("Ingresa tu nombre: ")
        cliente_socket.send(nombre_cliente.encode('utf-8'))
        
        respuesta = cliente_socket.recv(1024).decode('utf-8')
        print(f"Servidor: {respuesta}")
        
        print("\n--- Chat iniciado (escribe 'close' para salir) ---")
        
        hilo_recibir = threading.Thread(target=recibir_mensajes, args=(cliente_socket, nombre_cliente))
        hilo_recibir.daemon = True
        hilo_recibir.start()
        
        while True:
            mensaje = input("Tu mensaje: ")
            cliente_socket.send(mensaje.encode('utf-8'))
            
            if mensaje.lower() == "close":
                break
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cliente_socket.close()

empezar_cliente()