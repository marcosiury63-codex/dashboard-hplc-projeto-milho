DASHBOARD HPLC - PROJETO MILHO

1. Instale o Python 3.11 ou mais recente.

2. Abra o terminal dentro desta pasta.

3. Crie um ambiente virtual (recomendado):
   Windows:
     python -m venv .venv
     .venv\Scripts\activate

4. Instale as bibliotecas:
     pip install -r requirements.txt

5. Execute o dashboard:
     streamlit run app.py

6. O navegador abrira automaticamente.
   Se nao abrir, copie o endereco mostrado no terminal, normalmente:
     http://localhost:8501

ARQUIVO DE DADOS
O projeto ja inclui o arquivo 'Projeto Milho - Marcos.xlsx'.
Se quiser usar uma nova versao da planilha no futuro, voce pode:
- substituir o arquivo mantendo o mesmo nome e estrutura; ou
- usar o botao de upload na barra lateral do dashboard.

IMPORTANTE
Na planilha original, 'n.a.' significa 'nao detectado'.
O codigo trata esses valores como ausentes (NaN), nao como zero.
