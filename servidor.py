#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor de chat multicliente (TCP) optimizado para baja latencia.
- Usa selectors (sin hilos) para multiplexar varios sockets.
- Desactiva Nagle (TCP_NODELAY) para que los mensajes fluyan sin retraso.
- Timeout del selector reducido a 0.2s para mayor reactividad.
"""
import argparse
import selectors
import socket
import types
from datetime import datetime

CODIFICACION = "utf-8"

def hora():
    return datetime.now().strftime("%H:%M:%S")

def aceptar_conexion(sock, sel):
    """Acepta una conexión entrante y la registra en el selector."""
    try:
        conn, addr = sock.accept()
        conn.setblocking(False)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # baja latencia
        data = types.SimpleNamespace(addr=addr, nombre=None)
        sel.register(conn, selectors.EVENT_READ, data=data)
        print(f"[{hora()}] + Nueva conexión de {addr}")
    except Exception as e:
        print(f"[{hora()}] ! Error aceptando conexión: {e}")

def cerrar_conexion(sel, conn, data, razon="desconexión"):
    try:
        sel.unregister(conn)
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass
    print(f"[{hora()}] - {data.addr} cerró ({razon})")

def difundir(sel, emisor_conn, payload: bytes):
    """Envía el mensaje a todos los clientes excepto al emisor."""
    for key in sel.get_map().values():
        if key.data is None or key.fileobj is emisor_conn:
            continue
        try:
            key.fileobj.sendall(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print(f"[{hora()}] ! Error al difundir a {getattr(key.data,'addr','?')}: {e}")

def ejecutar_servidor(host: str, puerto: int):
    sel = selectors.DefaultSelector()
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind((host, puerto))
    lsock.listen()
    lsock.setblocking(False)
    lsock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sel.register(lsock, selectors.EVENT_READ, data=None)

    print(f"[{hora()}] Servidor escuchando en {host}:{puerto}")
    print(f"[{hora()}] Ctrl+C para detener.")

    try:
        while True:
            eventos = sel.select(timeout=0.2)  # menor latencia
            for key, mask in eventos:
                if key.data is None:
                    aceptar_conexion(key.fileobj, sel)
                else:
                    conn = key.fileobj
                    data = key.data
                    try:
                        recibido = conn.recv(4096)
                    except ConnectionResetError:
                        cerrar_conexion(sel, conn, data, razon="reset")
                        continue
                    except Exception as e:
                        print(f"[{hora()}] ! Error de lectura desde {data.addr}: {e}")
                        cerrar_conexion(sel, conn, data, razon="lectura")
                        continue

                    if recibido:
                        texto = recibido.decode(CODIFICACION, errors="replace").rstrip("\r\n")
                        if data.nombre is None and (texto.startswith("/nombre ") or texto.startswith("/name ")):
                            apodo = texto.split(" ", 1)[1].strip()[:20] or "anon"
                            data.nombre = apodo
                            bienvenida = f"[{hora()}] ~ {apodo} se unió desde {data.addr}\n"
                            print(bienvenida.strip())
                            difundir(sel, None, bienvenida.encode(CODIFICACION))
                            continue

                        emisor = data.nombre or f"{data.addr[0]}:{data.addr[1]}"
                        mensaje = f"[{hora()}] {emisor}: {texto}\n"
                        print(mensaje, end="")
                        difundir(sel, conn, mensaje.encode(CODIFICACION, errors="replace"))
                    else:
                        quien = data.nombre or f"{data.addr}"
                        adios = f"[{hora()}] ~ {quien} salió\n"
                        difundir(sel, None, adios.encode(CODIFICACION))
                        cerrar_conexion(sel, conn, data, razon="EOF")
    except KeyboardInterrupt:
        print(f"\n[{hora()}] Servidor detenido.")
    finally:
        sel.close()
        lsock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor de chat TCP rápido y simple")
    parser.add_argument("--host", default="0.0.0.0", help="Host/IP donde escuchar")
    parser.add_argument("--puerto", type=int, default=5000, help="Puerto TCP")
    args = parser.parse_args()
    ejecutar_servidor(args.host, args.puerto)
