#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente de chat por terminal optimizado para baja latencia.
- Usa dos hilos: recepción y entrada.
- Desactiva Nagle (TCP_NODELAY) para evitar retrasos.
- Reconecta automáticamente en caso de caída.
"""
import argparse
import socket
import sys
import threading
import time

CODIFICACION = "utf-8"

def bucle_recepcion(sock, detener_event):
    """Recibe mensajes del servidor y los imprime en pantalla."""
    try:
        while not detener_event.is_set():
            data = sock.recv(4096)
            if not data:
                print("\n[cliente] El servidor cerró la conexión.")
                break
            texto = data.decode(CODIFICACION, errors="replace")
            print(texto, end="", flush=True)
    except (ConnectionResetError, OSError):
        print("\n[cliente] Conexión perdida.")
    finally:
        detener_event.set()

def bucle_entrada(sock, detener_event, nombre=None):
    """Lee del teclado y envía mensajes al servidor."""
    try:
        if nombre:
            sock.sendall(f"/nombre {nombre}\n".encode(CODIFICACION))
        while not detener_event.is_set():
            linea = sys.stdin.readline()
            if not linea:
                break
            if linea.strip() in ("/salir", "/quit", "/exit"):
                detener_event.set()
                break
            try:
                sock.sendall(linea.encode(CODIFICACION, errors="replace"))
            except (BrokenPipeError, OSError):
                print("[cliente] No se pudo enviar; conexión rota.")
                detener_event.set()
                break
    finally:
        detener_event.set()

def conectar_con_reintentos(host, puerto):
    """Intenta conectar; si falla, reintenta con backoff exponencial."""
    demora = 1.0
    while True:
        try:
            s = socket.create_connection((host, puerto), timeout=10)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # baja latencia
            print(f"[cliente] Conectado a {host}:{puerto}")
            return s
        except OSError as e:
            print(f"[cliente] Falló la conexión: {e}. Reintentando en {int(demora)}s...")
            time.sleep(demora)
            demora = min(demora * 2, 30)

def ejecutar_cliente(host, puerto, nombre=None):
    while True:
        sock = conectar_con_reintentos(host, puerto)
        detener = threading.Event()

        t_recv = threading.Thread(target=bucle_recepcion, args=(sock, detener), daemon=True)
        t_recv.start()

        try:
            bucle_entrada(sock, detener, nombre=nombre)
        except KeyboardInterrupt:
            print("\n[cliente] Interrumpido por el usuario.")
            detener.set()
        finally:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass

        if detener.is_set():
            eleccion = input("[cliente] ¿Reconectar? (S/n): ").strip().lower()
            if eleccion == "n":
                print("[cliente] Adiós.")
                return
            else:
                print("[cliente] Reconectando...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente de chat rápido")
    parser.add_argument("--host", default="127.0.0.1", help="Host/IP del servidor")
    parser.add_argument("--puerto", type=int, default=5000, help="Puerto TCP del servidor")
    parser.add_argument("--nombre", default=None, help="Apodo opcional")
    args = parser.parse_args()
    ejecutar_cliente(args.host, args.puerto, nombre=args.nombre)
