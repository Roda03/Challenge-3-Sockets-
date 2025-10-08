import socket

SERVER_IP = "127.0.0.1"
SERVER_PORT = 8000

def run_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER_IP, SERVER_PORT))
    print(f"Conectado a {SERVER_IP}:{SERVER_PORT}. Escribe 'close' para salir.")

    try:
        # 1) Enviar nombre de usuario
        nombre = input("Ingrese su nombre: ").strip() or "Anon"
        client.sendall(nombre.encode("utf-8"))

        # Leer ACK (opcional)
        try:
            ack = client.recv(1024).decode("utf-8", errors="replace")
            if ack.lower() != "accepted":
                print("Aviso: el servidor no respondió 'accepted' al nombre (protocolo distinto).")
        except Exception:
            pass

        # 2) Loop de chat
        while True:
            msg = input("> ")

            # Enviar mensaje
            client.sendall(msg.encode("utf-8")[:1024])

            # Leer respuesta del servidor
            resp = client.recv(1024)
            if not resp:
                print("El servidor cerró la conexión.")
                break

            resp_text = resp.decode("utf-8", errors="replace").strip()
            print("Servidor:", resp_text)

            if resp_text.lower() == "closed":
                print("Conexión cerrada por el servidor.")
                break

    except Exception as e:
        print("Error en el cliente:", e)
    finally:
        try:
            client.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        client.close()
        print("Cliente cerrado.")

if __name__ == "__main__":
    run_client()
