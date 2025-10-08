import socket
import threading
import signal
import sys
import time

SERVER_IP = "127.0.0.1"   # usa "0.0.0.0" para aceptar desde otras PCs de la red
SERVER_PORT = 8000

# Variables globales para control del servidor
server_sock = None
shutdown_event = threading.Event()
active_connections = []

def handle_client(client_socket: socket.socket, addr):
    """
    Atiende a un cliente en un hilo dedicado.
    Protocolo:
      1) Primer mensaje: 'username' (texto)
      2) Mensajes libres; si recibe 'close' => responde 'closed' y cierra
    """
    # Registrar esta conexión
    active_connections.append(client_socket)
    
    try:
        # 1) Leer username
        data = client_socket.recv(1024)
        if not data:
            return
        username = data.decode("utf-8", errors="replace").strip() or f"{addr[0]}:{addr[1]}"
        print(f"[+] {username} conectado desde {addr[0]}:{addr[1]}")

        # Opcional: ACK del nombre
        client_socket.sendall(b"accepted")

        # 2) Loop de mensajes
        while not shutdown_event.is_set():
            # Usar timeout para verificar periódicamente si debemos cerrar
            client_socket.settimeout(1.0)
            try:
                data = client_socket.recv(1024)
                if not data:
                    # Cliente cerró su lado de la conexión
                    break

                msg = data.decode("utf-8", errors="replace").strip()

                if msg.lower() == "close":
                    client_socket.sendall(b"closed")
                    break

                print(f"{username}: {msg}")
                client_socket.sendall(b"accepted")
            except socket.timeout:
                # Timeout para verificar si debemos cerrar
                continue
            except Exception as e:
                if not shutdown_event.is_set():
                    print(f"[!] Error con {addr}: {e}")
                break
    except Exception as e:
        if not shutdown_event.is_set():
            print(f"[!] Error con {addr}: {e}")
    finally:
        # Remover de conexiones activas y cerrar
        if client_socket in active_connections:
            active_connections.remove(client_socket)
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        client_socket.close()
        if not shutdown_event.is_set():
            print(f"[-] Conexión cerrada: {addr[0]}:{addr[1]}")

def run_server():
    global server_sock
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Reusar puerto rápidamente tras reinicio
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_sock.bind((SERVER_IP, SERVER_PORT))
    server_sock.listen(128)  # backlog razonable
    print(f"Servidor escuchando en {SERVER_IP}:{SERVER_PORT} (Ctrl+C para detener)")

    while not shutdown_event.is_set():
        try:
            # Usar timeout para poder verificar shutdown_event periódicamente
            server_sock.settimeout(1.0)
            client_socket, addr = server_sock.accept()
            
            # Hilo por cliente (no daemon para permitir cierre limpio)
            t = threading.Thread(target=handle_client, args=(client_socket, addr))
            t.start()
            
        except socket.timeout:
            # Timeout normal, verificar si debemos cerrar
            continue
        except OSError as e:
            if not shutdown_event.is_set():
                print(f"[!] Error aceptando conexión: {e}")
            break

def stop_server(sig, frame):
    print("\nDeteniendo servidor...")
    shutdown_event.set()
    
    # Cerrar socket del servidor
    if server_sock is not None:
        try:
            server_sock.close()
        except Exception:
            pass
    
    # Cerrar todas las conexiones activas
    print("Cerrando conexiones activas...")
    for conn in active_connections[:]:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
    
    print("Servidor detenido correctamente")
    sys.exit(0)

if __name__ == "__main__":
    # Captura Ctrl+C para cierre ordenado
    signal.signal(signal.SIGINT, stop_server)
    
    try:
        run_server()
    except KeyboardInterrupt:
        stop_server(None, None)
    except Exception as e:
        print(f"Error inesperado: {e}")
        stop_server(None, None)