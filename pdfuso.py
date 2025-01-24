import tkinter as tk
from tkinter import filedialog, Toplevel, Text, messagebox
import pdfplumber
from datetime import datetime, timedelta
import re

# Função para verificar se a unidade é MB ou GB
def is_mb_or_gb(value):
    return "MB" in value or "GB" in value

# Função para processar o PDF e encontrar as datas de uso
def process_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            connections = []
            last_date_in_report = None  # Variável para armazenar a data final dos filtros

            for page in pdf.pages:
                text = page.extract_text()

                # Procurar a data final no cabeçalho (padrão dd/mm/yyyy)
                match = re.search(r"Filtros:.*\|.*\|\s*\d{2}/\d{2}/\d{4}\s*\|\s*(\d{2}/\d{2}/\d{4})", text)
                if match:
                    last_date_in_report = datetime.strptime(match.group(1), "%d/%m/%Y")

                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and len(row) > 6 and row[5]:  # Verificar se a conexão inicial está presente
                            try:
                                # Data de conexão inicial
                                start_date = datetime.strptime(row[5].split(" ")[0], "%d/%m/%Y")
                                
                                # Verificar se a data de conexão final existe
                                if row[6]:
                                    end_date = datetime.strptime(row[6].split(" ")[0], "%d/%m/%Y")
                                else:
                                    # Se a data final estiver vazia, usamos a data extraída dos filtros
                                    end_date = last_date_in_report
                                
                                # Verificar se houve uso de dados significativo (download maior que 1 MB)
                                download_value = float(row[9].split()[0])  # Extrair o valor numérico do download
                                download_unit = row[9].split()[1]  # Extrair a unidade (MB, GB, etc.)
                                
                                if (download_unit == "MB" and download_value > 1) or download_unit == "GB":
                                    connections.append((start_date, end_date))
                            except (ValueError, IndexError):
                                continue  # Ignorar linhas que não contêm dados válidos

            if connections and last_date_in_report:
                connections.sort()  # Ordena por data inicial

                # Identificar saltos entre a conexão final e a próxima conexão inicial
                no_usage_dates = []
                for i in range(len(connections) - 1):
                    current_end = connections[i][1]
                    next_start = connections[i + 1][0]
                    
                    # Se houver um dia entre a conexão final atual e a próxima conexão inicial, considere sem uso
                    delta_days = (next_start - current_end).days
                    if delta_days > 1:
                        no_usage_dates.extend([
                            (current_end + timedelta(days=d)).strftime("%d/%m/%y")
                            for d in range(1, delta_days)
                        ])
                
                # Verificar se a última conexão tem download baixo ou vazio e adicionar dias sem uso até a data dos filtros
                last_connection_end = connections[-1][1]
                if last_connection_end < last_date_in_report:
                    # Evitar incluir o dia da emissão do relatório como sem uso
                    if last_connection_end + timedelta(days=1) < last_date_in_report:
                        last_to_report_days = (last_date_in_report - last_connection_end).days
                        no_usage_dates.extend([
                            (last_connection_end + timedelta(days=d)).strftime("%d/%m/%y")
                            for d in range(1, last_to_report_days + 1)
                        ])

                # Determinar as primeiras e últimas datas com acesso
                first_date = connections[0][0].strftime("%d/%m/%y")
                last_date = last_date_in_report.strftime("%d/%m/%y")

                # Preparar a mensagem para exibição
                no_usage_message = "Nenhum dia sem uso detectado."
                if no_usage_dates:
                    no_usage_message = f"Dias sem uso (menor que MBs): {', '.join(no_usage_dates)}"

                result_message = f"Utilizou de {first_date} até {last_date}\n{no_usage_message}"
                
                # Exibir o resultado em uma nova janela, com texto copiável e dark mode
                result_window = Toplevel(root)
                result_window.title(f"Resultado - {file_path.split('/')[-1]}")
                
                # Ajustar o tamanho da janela baseado no conteúdo
                result_message_lines = result_message.count("\n") + 1
                result_window.geometry(f"600x{100 + result_message_lines * 20}")
                
                # Dark mode
                result_window.configure(bg="#2c2c2c")
                
                text_widget = Text(result_window, wrap="word", font=("Helvetica", 14), bg="#2c2c2c", fg="#ffffff")
                text_widget.insert("1.0", result_message)
                text_widget.tag_configure("center", justify="center")
                text_widget.tag_add("center", "1.0", "end")
                text_widget.pack(expand=True, fill="both")
                text_widget.config(state="disabled")  # Impedir a edição, permitindo apenas seleção e cópia

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao processar o PDF: {str(e)}")

# Função para abrir o diálogo de seleção de arquivo
def open_file():
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        process_pdf(file_path)

# Configuração da interface gráfica com dark mode e centralização
root = tk.Tk()
root.title("Analisador de Uso de Dados")
root.configure(bg="#2c2c2c")
root.geometry("600x400")  # Janela centralizada
root.eval('tk::PlaceWindow . center')  # Centralizar a janela

frame = tk.Frame(root, padx=60, pady=60, bg="#2c2c2c")
frame.pack(expand=True)

label = tk.Label(frame, text="Selecione o relatório de uso:", font=("Helvetica", 14), fg="#ffffff", bg="#2c2c2c")
label.pack(pady=20)

button = tk.Button(frame, text="Abrir PDF", command=open_file, font=("Helvetica", 14), bg="#4a4a4a", fg="#ffffff")
button.pack(pady=20)

root.mainloop()
