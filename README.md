# dashboard-hplc-projeto-milho
Dashboard interativo para análise dos resultados cromatográficos do Projeto

Execute com `pip install -r requirements.txt` e `streamlit run app.py`.

Os gráficos exibem barras de ± desvio padrão amostral (divisor n−1) por
tratamento e tempo. O erro relativo é `100 × DP / |média|`, apresentado ao
passar o mouse sobre os pontos e em uma tabela exportável em CSV. As médias
e o desvio padrão usam apenas leituras numéricas disponíveis: geralmente
triplicatas; para os açúcares em 0 h, a planilha contém duas leituras.
Com menos de duas leituras, o DP fica indisponível; com média zero, o erro
relativo fica indisponível.

O etanol em 0 h é representado por zero assumido, com DP e erro relativo
zero e n=0, quando esse tempo está selecionado. Esse ponto é identificado
nos gráficos e nas estatísticas; a planilha e a tabela de leituras originais
continuam preservando os valores ausentes. Medições numéricas de etanol
em 0 h em uma nova planilha são respeitadas.

DP4+, DP3, DP2, glicose e frutose usam a mesma escala Y, com origem zero e
margem para as barras de erro. A faixa de referência do DP4+ é ampliada
para todos os açúcares se outro carboidrato a ultrapassar após os filtros.
Nas curvas de réplicas individuais, as barras e o erro relativo indicam a
dispersão do tratamento/tempo, e não uma estimativa separada por réplica.

Ao passar o mouse, a descrição mostra apenas o ponto mais próximo, com fundo
escuro, média e DP com quatro casas decimais e erro relativo com duas casas.
A legenda fica abaixo do gráfico e se ajusta à largura disponível. No modo
de réplicas, cada tratamento aparece uma vez na legenda, e o nome da réplica
continua na descrição do ponto.

Para validar os cálculos e as interações do dashboard:
`pip install pytest` e `python -m pytest -q`.
