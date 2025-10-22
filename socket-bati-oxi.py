import time
import socket
import json
import statistics
import numpy as np 
from max30102 import MAX30102
import hrcalc

# --- Configurações ---
HOST = '127.0.0.1'
PORT = 65433
AMOSTRAS_PARA_COLETAR = 100 
BPM_MIN_VALIDO = 40
BPM_MAX_VALIDO = 200
SPO2_MIN_VALIDO = 85
SPO2_MAX_VALIDO = 100

# Listas para coletar as amostras válidas
leituras_bpm = []
leituras_spo2 = []

def processar_e_enviar_dados(conn):
    """
    Filtra, calcula medianas e envia o JSON.
    Retorna True se enviou, False se descartou o lote.
    """
    global leituras_bpm, leituras_spo2
    print("\nProcessando lote de amostras...")
    bpm_validos = [b for b in leituras_bpm if BPM_MIN_VALIDO <= b <= BPM_MAX_VALIDO]
    spo2_validos = [s for s in leituras_spo2 if SPO2_MIN_VALIDO <= s <= SPO2_MAX_VALIDO]
    print(f"    Leituras de BPM válidas ({len(bpm_validos)}/{len(leituras_bpm)}): {bpm_validos}")
    print(f"    Leituras de SpO2 válidas ({len(spo2_validos)}/{len(leituras_spo2)}): {spo2_validos}")
    bpm_final = round(statistics.median(bpm_validos)) if bpm_validos else None
    spo2_final = round(statistics.median(spo2_validos)) if spo2_validos else None
    
    # Limpa as listas para o próximo lote
    leituras_bpm.clear()
    leituras_spo2.clear()

    if bpm_final is not None and spo2_final is not None:
        data_json = {"bpm": bpm_final, "spo2": spo2_final}
        mensagem_json = json.dumps(data_json).encode('utf-8')
        conn.sendall(mensagem_json)
        print(f" JSON enviado para o cliente: {mensagem_json.decode('utf-8')}")
        return True # <-- MUDANÇA 1: Retorna True em caso de sucesso
    else:
        print(" Lote descartado, poucos dados válidos. Continue com o dedo no sensor.\n")
        return False # <-- MUDANÇA 2: Retorna False em caso de falha

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor de Oximetria iniciado. Aguardando conexão em {HOST}:{PORT}...")
        
        while True:
            conn, addr = s.accept()
            with conn:
                print(f" Cliente conectado: {addr}")
                
                # --- LÓGICA DE LEITURA REPLICADA DO REPOSITÓRIO ---
                sensor = MAX30102()
                ir_data = []
                red_data = []
                
                leituras_bpm.clear()
                leituras_spo2.clear()
                
                print("Sensor MAX30102 iniciado. Coloque o dedo no sensor.")
                
                try:
                    while True: # Loop principal de leitura
                        # 1. Verifica quantos dados estão esperando no buffer do sensor
                        num_bytes = sensor.get_data_present()
                        
                        if num_bytes > 0:
                            # 2. Lê todos os dados da fila (FIFO)
                            while num_bytes > 0:
                                red, ir = sensor.read_fifo()
                                num_bytes -= 1
                                ir_data.append(ir)
                                red_data.append(red)
                            
                            # 3. Mantém os buffers com um tamanho máximo de 100 (janela deslizante)
                            while len(ir_data) > 100:
                                ir_data.pop(0)
                                red_data.pop(0)

                            # 4. Se temos 100 amostras, podemos calcular BPM e SpO2
                            if len(ir_data) == 100:
                                bpm, valid_bpm, spo2, valid_spo2 = hrcalc.calc_hr_and_spo2(ir_data, red_data)
                                
                                # 5. Lógica de detecção de dedo (igual à do repositório)
                                # Se a intensidade média da luz for muito baixa, não há dedo
                                if (np.mean(ir_data) < 50000 and np.mean(red_data) < 50000):
                                    print("Finger not detected. Waiting...")
                                    # Limpa nossas listas se o dedo for removido
                                    leituras_bpm.clear()
                                    leituras_spo2.clear()
                                    continue # Volta para o início do loop

                                # 6. Se os dados são válidos, adiciona às nossas listas de coleta
                                if valid_bpm and valid_spo2:
                                    leituras_bpm.append(bpm)
                                    leituras_spo2.append(spo2)
                                    print(f"    Leitura válida... BPM={int(bpm)}, SpO2={int(spo2)}  (Amostras: {len(leituras_bpm)}/{AMOSTRAS_PARA_COLETAR})")
                                    
                                    # 7. Se coletamos amostras suficientes, processa o lote e envia
                                    if len(leituras_bpm) >= AMOSTRAS_PARA_COLETAR:
                                        # --- MUDANÇA 3: Verifica o retorno da função ---
                                        sucesso_envio = processar_e_enviar_dados(conn)
                                        
                                        if sucesso_envio:
                                            print(f"🔌 Desconectando cliente {addr}...\n")
                                            break # <-- Sai do loop 'while True' interno
                                        # Se sucesso_envio for False, o loop continua
                                        # para tentar coletar um novo lote de 100 amostras.

                        # Pequena pausa para não sobrecarregar a CPU
                        time.sleep(0.01)

                except (ConnectionResetError, BrokenPipeError):
                    print(f" Cliente {addr} desconectou.")
                except KeyboardInterrupt:
                    print("\nPrograma encerrado pelo usuário.")
                    sensor.shutdown() # Garante que o sensor desliga no Ctrl+C
                    break
                finally:
                    # Desliga o sensor para apagar os LEDs
                    sensor.shutdown()
                    print(" Conexão encerrada e sensor desligado.")

if __name__ == "__main__":
    main()