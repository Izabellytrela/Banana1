from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import numpy as np
import cv2
from sklearn.cluster import KMeans
import gdown

app = Flask(__name__)

# Função para executar seu código
def executar_meu_codigo():
    # Autenticação com o Google Sheets usando credenciais
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    # Abrir a planilha e selecionar a aba pelo título
    spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1uTGil123c-mqMiysxt3-YF-ZPrpx2KXUyK8PvrSU9v8/edit#gid=0'
    spreadsheet = client.open_by_url(spreadsheet_url)
    sheet = spreadsheet.worksheet("Resultado Python - Mamão")

    # Pegar o número da última linha
    last_row_number = len(sheet.get_all_values())

    # Pegar o link da última linha da primeira coluna
    image_url = sheet.cell(last_row_number, 1).value

    if 'drive.google.com' in image_url:
        file_id = image_url.split('/')[-2]
        download_url = f'https://drive.google.com/uc?id={file_id}'
        output_image = 'image_downloaded.jpg'
        gdown.download(download_url, output_image, quiet=False)

        try:
            image = Image.open(output_image)
            image_cv = np.array(image)
            image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)

            # Funções de processamento
            def obter_cor_dominante(image, k=5):
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                reshaped_image = rgb_image.reshape((-1, 3))
                kmeans = KMeans(n_clusters=k)
                kmeans.fit(reshaped_image)
                cores_dominantes = kmeans.cluster_centers_
                labels = kmeans.labels_
                counts = np.bincount(labels)
                cor_dominante = cores_dominantes[np.argmax(counts)]
                return cor_dominante.astype(int)

            def classificar_maturacao(cor_dominante):
                r, g, b = cor_dominante
                if r < 100 and g > 100 and b > 20 and b < 35:
                    return "C1 - Mamão verde (não maduro)"
                elif r > 100 and r < 120 and g > 100 and b < 20:
                    return "C2 - Mamão verde-amarelado"
                elif r > 125 and r < 175  and g > 115 and g < 160 and b < 15:
                    return "C3 - Mamão amarelo-esverdeado"
                elif r > 190 and r < 210 and g > 155 and b < 50:
                    return "C4 - Mamão amarelo"
                elif r > 210 and g > 130 and b < 20:
                   return "C5 - Mamão passado"
                else:
                    return "Maturação não identificada"

            def avaliar_venda(fase_maturacao):
                if fase_maturacao in ["C3 - Mamão amarelo-esverdeado", "C4 - Mamão amarelo"]:
                    return "Aprovado para venda"
                else:
                    return "Reprovado para venda"

            # Processar a imagem
            cor_dominante = obter_cor_dominante(image_cv)
            fase_maturacao = classificar_maturacao(cor_dominante)
            status_venda = avaliar_venda(fase_maturacao)

            # Atualizar o status na planilha
            sheet.update_cell(last_row_number, 2, status_venda)

        except IOError:
            print("Erro ao abrir a imagem. Verifique se o arquivo é válido.")
    else:
        print("O link fornecido não é um link válido do Google Drive.")

# Definir a rota do webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    executar_meu_codigo()
    return "Webhook recebido e código executado", 200

# Iniciar o servidor Flask na porta fornecida pelo Cloud Run
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
