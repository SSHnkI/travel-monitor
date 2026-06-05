# Travel Monitor

Aplicação pessoal e simples para monitorar preços de **passagens aéreas, hospedagens e passagens rodoviárias** de destinos definidos em um arquivo YAML. Quando encontra um preço abaixo do limite configurado ou uma queda em relação ao histórico, envia um alerta por e-mail. Roda gratuitamente no GitHub Actions.

## Funcionalidades

- Configuração 100% em `config.yaml` (destinos, limites de preço, e-mail).
- Histórico de preços persistido em JSON.
- Alertas por e-mail via SMTP.
- Execução automática agendada via GitHub Actions (custo zero em repositório público).
- Arquitetura modular com **provedores plugáveis** — adicionar uma nova fonte é criar um arquivo.
- Logs em arquivo (rotativos) e console; tratamento de erros isolado por destino.

## Estrutura do projeto

```
travel-monitor/
├── main.py                    # ponto de entrada
├── config.yaml.example        # modelo de configuração (copie para config.yaml)
├── config.scraper.example.yaml# modelo usando web scraping (11 sites)
├── requirements.txt
├── README.md
├── .gitignore
├── tools/
│   └── inspect.py             # descobre seletores CSS de preço dos sites
├── .github/
│   └── workflows/
│       └── monitor.yml        # agendamento no GitHub Actions
├── data/
│   └── history.json           # histórico de preços (gerado/atualizado)
├── logs/                      # logs rotativos (ignorados pelo git)
└── src/
    ├── __init__.py
    ├── config.py              # carrega/valida YAML + variáveis de ambiente
    ├── logger.py              # logging centralizado
    ├── history.py             # leitura/escrita do histórico JSON
    ├── notifier.py            # envio de e-mail SMTP
    ├── monitor.py             # lógica central (decide quando alertar)
    └── providers/
        ├── __init__.py        # registry com autoimport
        ├── base.py            # classe Provider + @register + Offer
        ├── mock.py            # provedor de demonstração (sem API/custo)
        ├── amadeus.py         # exemplo de provedor real de voos (tier grátis)
        └── scraper.py         # web scraping genérico (requests/Playwright)
```

## Requisitos

- Python 3.12

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/travel-monitor.git
cd travel-monitor

# 2. (Opcional) crie um ambiente virtual
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Crie sua configuração a partir do exemplo
cp config.yaml.example config.yaml
# edite config.yaml com seus destinos e dados de e-mail
```

## Execução local

```bash
python main.py                   # usa config.yaml
python main.py -c outra.yaml     # config alternativa
```

A primeira execução não dispara alertas de "queda" (não há histórico), apenas
alertas de preço abaixo do limite. As execuções seguintes comparam com o
histórico salvo em `data/history.json`.

## Configuração de e-mail

No `config.yaml`, preencha o bloco `email`. Para o Gmail, gere uma **Senha de
app** (com verificação em duas etapas ativada) e use-a no lugar da senha normal.

Em produção (GitHub Actions), **não** coloque segredos no YAML. Use Secrets do
repositório — as variáveis de ambiente têm prioridade sobre o arquivo:

| Variável         | Descrição                                   |
|------------------|---------------------------------------------|
| `SMTP_HOST`      | servidor SMTP (ex.: smtp.gmail.com)         |
| `SMTP_PORT`      | porta (ex.: 587)                            |
| `SMTP_USER`      | usuário/login                               |
| `SMTP_PASSWORD`  | senha (ou senha de app)                     |
| `SMTP_FROM`      | remetente (padrão: SMTP_USER)               |
| `ALERT_TO`       | destinatários separados por vírgula         |

## Execução automática no GitHub Actions

1. Suba o projeto para um repositório no GitHub (público = minutos gratuitos ilimitados).
2. Em **Settings → Secrets and variables → Actions**, cadastre os secrets da
   tabela acima (e, se for usar voos reais, `AMADEUS_CLIENT_ID` e
   `AMADEUS_CLIENT_SECRET`).
3. O workflow `.github/workflows/monitor.yml` roda diariamente às 09:00 UTC e
   também pode ser disparado manualmente em **Actions → Travel Monitor → Run workflow**.
4. Após cada execução, o histórico atualizado é commitado de volta ao repositório.

> Ajuste o horário alterando o `cron` no workflow.

## Adicionando um novo provedor

O sistema descobre provedores automaticamente. Para criar um novo:

1. Crie `src/providers/meu_provedor.py`.
2. Implemente uma classe que herde de `Provider` e a decore com `@register("nome")`.
3. Implemente `fetch_offers(params)` retornando uma lista de `Offer`.
4. Use `provider: nome` no `config.yaml`.

Exemplo mínimo:

```python
from .base import Offer, Provider, register

@register("meu_provedor")
class MeuProvedor(Provider):
    kind = "hotel"

    def fetch_offers(self, params):
        # chamar a API real aqui...
        return [Offer(price=199.90, currency="BRL", details="Hotel X")]
```

Veja `src/providers/amadeus.py` como modelo de integração com API real
(autenticação OAuth, requisição, normalização para `Offer`). O `mock.py` permite
testar todo o fluxo sem nenhuma chave de API.

## Web scraping (sem APIs pagas)

O provedor `scraper` (`src/providers/scraper.py`) permite monitorar sites de
viagem diretamente, sem APIs pagas. Ele é **configurável pelo YAML**: você
informa a URL, um seletor CSS de preço e a moeda — sem escrever código por site.

### Já vem funcionando

O `config.yaml.example` já traz **dois destinos reais validados**, com seletores
capturados dos sites:

- **ClickBus** (rodoviário) — `[data-testid='price-container']`. Funciona bem no
  GitHub Actions. Para trocar a rota, abra o ClickBus, faça a busca uma vez e
  copie da URL os *slugs* de origem/destino (ex.: `sao-paulo-sp-todos`,
  `rio-de-janeiro-rj-todos`).
- **Booking** (hospedagem) — `[data-testid='price-and-discounted-price']`. O preço
  é o **total da estadia** (não por noite). O Booking tem anti-bot e pode
  bloquear o IP do GitHub Actions; se isso ocorrer, rode este destino localmente.

> **Voos (Google Flights, Skyscanner etc.):** não vêm pré-configurados de
> propósito. O Google Flights exige um token de busca (`tfs`) que não dá para
> montar por URL simples, e bloqueia o GitHub Actions. Para voos, o caminho
> confiável e gratuito é a **API de teste da Amadeus** (tier grátis, sem
> pagamento) — veja `src/providers/amadeus.py`. O arquivo
> `config.scraper.example.yaml` traz outros sites como modelo (seletores `TODO`).

### Configurando um site novo:

1. Descubra o seletor de preço (os do exemplo estão marcados como `TODO`):

   ```bash
   python tools/inspect.py "<URL completa do site>" --wait-for "<container da lista>"
   ```

   O script abre a página com Playwright, encontra os elementos que parecem
   preço e sugere seletores CSS candidatos. Cole o melhor em `price_selector`.

2. Para sites que carregam preços via JavaScript (a maioria), use `render_js: true`.
   Instale o navegador uma vez:

   ```bash
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

Avisos importantes sobre scraping:

- **Anti-bot:** Google Flights, Booking e Skyscanner têm proteção agressiva e
  podem bloquear o IP do GitHub Actions. Se acontecer, rode localmente ou troque
  o destino. ClickBus e sites menores costumam funcionar melhor.
- **Fragilidade:** os sites mudam o HTML com frequência e os seletores quebram.
  Por isso eles ficam no YAML, fáceis de reajustar com `tools/inspect.py`.
- **Termos de uso:** scraping pode violar os ToS dos sites. Use baixa frequência
  e por conta própria.

## Como funciona o fluxo

1. Lê os destinos do `config.yaml`.
2. Para cada destino, instancia o provedor indicado e consulta as ofertas.
3. Escolhe a de menor preço (melhor oferta).
4. Compara com o último preço salvo no histórico.
5. Se o preço estiver abaixo do `max_price` **ou** houver queda relevante
   (`min_drop_percent`), adiciona um alerta.
6. Envia um único e-mail com todos os alertas e salva o novo histórico.

## Logs e erros

- Logs em `logs/travel_monitor.log` (rotativos, até 4 arquivos) e no console.
- Erros de um destino são registrados e **não** interrompem os demais.
- Códigos de saída: `0` sucesso, `1` falha inesperada, `2` config inválida.

## Custo

Usando repositório público + provedor `mock` (ou tiers gratuitos como o da
Amadeus em ambiente de teste), o projeto roda **sem custo**.
