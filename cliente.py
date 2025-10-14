import socket, threading, time  # sockets TCP, hilos para concurrencia y tiempo para backoff

# --- Conexión con reintentos ---
def conectar_con_reintentos(host, port, reintentos=5, espera=0.5):
    for i in range(reintentos):  # intenta varias veces con backoff exponencial
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # crea socket TCP/IPv4
            s.connect((host, port))  # intenta conectar al servidor
            return s  # conexión exitosa
        except Exception as e:
            if i == reintentos - 1: raise  # en el último intento relanza el error
            print(f"Conexión fallida ({e}). Reintento en {espera:.1f}s...")
            time.sleep(espera)  # espera antes del próximo intento
            espera *= 2  # backoff exponencial para no saturar

# --- Sincronización ---
reconnect_lock = threading.Lock()  # evita que dos hilos reconecten al mismo tiempo
stop_event = threading.Event()      # señal para pedir cierre ordenado del receptor

def reconectar(sock_holder, host, port, nombre):
    # si otro hilo ya reconecta, esperamos a que termine y reutilizamos su resultado
    if not reconnect_lock.acquire(blocking=False):
        with reconnect_lock:
            return sock_holder[0] is not None  # true si ya quedó un socket válido

    try:
        print("\n🔄 Reconectando...")
        s = conectar_con_reintentos(host, port, reintentos=7, espera=0.5)  # reconexión con backoff
        s.send(nombre.encode("utf-8"))  # reenvía el nombre como handshake simple
        try:
            print("Servidor:", s.recv(1024).decode("utf-8"))  # intento de leer saludo del servidor
        except:
            pass  # si no hay saludo no es crítico

        # cerramos el socket viejo y reemplazamos el actual
        try:
            if sock_holder[0]:
                sock_holder[0].close()
        except:
            pass
        sock_holder[0] = s  # actualizamos el socket compartido
        print("✅ Reconectado.\nTu mensaje: ", end="", flush=True)  # restauramos el prompt
        return True  # reconexión exitosa
    except Exception as e:
        print(f"❌ No se pudo reconectar: {e}")
        return False  # reconexión fallida
    finally:
        reconnect_lock.release()  # liberamos el lock de reconexión

# --- Hilo receptor con Event ---
def recibir_mensajes(sock_holder, mi_nombre, host, port):
    while not stop_event.is_set():  # se mantiene escuchando mientras no pidamos cerrar
        try:
            sock_holder[0].settimeout(1.0)  # timeout corto para poder revisar stop_event periódicamente
            data = sock_holder[0].recv(1024)  # intenta recibir datos del servidor

            if not data:  # recv() vacío indica cierre del peer
                if stop_event.is_set():
                    break  # ya estamos cerrando, salir
                if reconectar(sock_holder, host, port, mi_nombre):
                    continue  # reconectó, seguir recibiendo
                print("\nConexión cerrada por el servidor.")
                break  # no se pudo reconectar

            msg = data.decode("utf-8").rstrip("\r\n")  # decodifica y limpia fin de línea
            print('\r\033[K', end='', flush=True)  # borra la línea del prompt
            # decide si el mensaje es propio o de otro para etiquetarlo
            if ":" in msg and not msg.startswith(mi_nombre + ":"):
                print(f"👤 {msg}")  # mensaje de otro usuario
            else:
                print(f"📢 {msg}")  # mensaje propio o del servidor
            print("Tu mensaje: ", end="", flush=True)  # repone el prompt

        except socket.timeout:
            continue  # tiempo agotado, vuelve a intentar y revisa stop_event
        except Exception as e:
            if stop_event.is_set():
                break  # si estamos cerrando, salir sin ruido
            # si hubo error de red, intentar reconectar
            if reconectar(sock_holder, host, port, mi_nombre):
                continue  # reconectó, seguir recibiendo
            print(f"\nError recibiendo: {e}")
            break  # no se pudo reconectar

# --- Cliente principal (usa stop_event en el cierre) ---
def empezar_cliente():
    host, port = "127.0.0.1", 8000  # destino del servidor
    s = conectar_con_reintentos(host, port, reintentos=5, espera=0.5)  # conexión inicial con backoff
    print(f"Conectado al servidor en {host}:{port}")
    nombre = input("Ingresa tu nombre: ")  # nombre del usuario para identificar mensajes
    s.send(nombre.encode("utf-8"))  # handshake: enviamos el nombre al servidor
    try:
        print("Servidor:", s.recv(1024).decode("utf-8"))  # mostramos el saludo si llega
    except:
        pass  # si no llega el saludo seguimos igual
    print("\n--- Chat iniciado (escribe 'close' para salir) ---")

    sock_holder = [s]  # contenedor mutable para poder reemplazar el socket desde otros hilos
    hilo_receptor = threading.Thread(
        target=recibir_mensajes,
        args=(sock_holder, nombre, host, port)
    )  # hilo que escucha mensajes entrantes en paralelo
    hilo_receptor.start()  # comienza el hilo receptor

    while True:  # bucle de envío desde la consola
        try:
            msg = input("Tu mensaje: ")  # lee lo que el usuario escribe
            if msg.lower() == "close":  # comando de salida
                try:
                    sock_holder[0].send(b"close")  # avisa al servidor el cierre
                except:
                    pass  # si ya está caído, no importa
                break  # salir del bucle principal

            try:
                sock_holder[0].send(msg.encode("utf-8"))  # intento de envío normal
            except Exception as e:
                print(f"\nError enviando ({e}). Intentando reconectar...")
                if reconectar(sock_holder, host, port, nombre):  # reconecta si es posible
                    try:
                        sock_holder[0].send(msg.encode("utf-8"))  # reintento único del último mensaje
                    except Exception as e2:
                        print(f"Error tras reconexión: {e2}")  # falló el reenvío tras reconectar
                else:
                    print("No se pudo reconectar para enviar")  # reconexión fallida
        except (EOFError, KeyboardInterrupt):
            print("\nCerrando cliente...")
            break  # cierre solicitado desde la terminal

    # Cierre ordenado con Event
    stop_event.set()  # señal para que el hilo receptor termine su bucle
    try:
        sock_holder[0].close()  # cierre del socket actual
    except:
        pass
    hilo_receptor.join(timeout=2.0)  # esperamos a que el receptor termine para evitar errores al apagar
    print("Cliente cerrado correctamente")  # confirmación de cierre

empezar_cliente()  # punto de entrada del cliente
