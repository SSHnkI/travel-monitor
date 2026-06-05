# Guia de instalacao — Travel Monitor (Brevo + GitHub pelo site)

Siga na ordem. Leva ~20 minutos. Voce nao precisa instalar nada no PC, nem
mexer na seguranca do seu Gmail.

---

## Parte 1 — Criar conta no Brevo e pegar as credenciais SMTP

O Brevo envia os e-mails por voce (gratis ate ~300/dia) e fornece um
login/senha SMTP proprios, sem 2FA.

1. Crie a conta em https://www.brevo.com (plano Free). Confirme seu e-mail.
2. **Validar o remetente** (obrigatorio — o Brevo so envia "de" e-mails
   verificados):
   - No painel, va em **Senders, Domains & Dedicated IPs > Senders**
     (ou acesse https://app.brevo.com/senders/list ).
   - Clique em **Add a sender**, preencha nome e o e-mail que sera o remetente
     (pode ser seu Gmail mesmo, ex.: `voce@gmail.com`).
   - O Brevo envia um e-mail de confirmacao para esse endereco. Abra e clique
     no link para validar.
3. **Pegar as credenciais SMTP**:
   - Acesse **SMTP & API > SMTP** (ou https://app.brevo.com/settings/keys/smtp ).
   - Anote os tres valores que a pagina mostra:
     - **Servidor (SMTP server):** normalmente `smtp-relay.brevo.com`
     - **Porta:** `587`
     - **Login:** o e-mail de login que aparece ali (ex.: `voce@gmail.com`
       ou um `xxxx@smtp-brevo.com`)
   - Clique em **Generate a new SMTP key** (ou "Create a new SMTP key"),
     de um nome (ex.: `travel-monitor`) e **copie a chave gerada**. Essa chave
     e a sua senha SMTP — guarde, pois ela so aparece uma vez.

> Resumo do que voce vai ter ao fim desta parte:
> - servidor SMTP (host), porta 587
> - login SMTP
> - a chave SMTP (senha)
> - o e-mail remetente validado

---

## Parte 2 — Criar o repositorio e subir os arquivos

1. Crie uma conta (ou entre) em https://github.com
2. Clique no **+** (canto superior direito) > **New repository**.
3. Em **Repository name**, coloque `travel-monitor`.
4. Marque **Public** (repositorio publico = GitHub Actions gratis e ilimitado).
5. **Nao** marque "Add a README". Clique em **Create repository**.
6. Na pagina seguinte, clique em **uploading an existing file**
   (ou **Add file > Upload files**).
7. Arraste os arquivos e pastas do projeto. Suba:
   - `main.py`, `requirements.txt`, `README.md`, `SETUP.md`, `.gitignore`,
     `config.yaml.example`, `config.scraper.example.yaml`
   - as pastas `src/`, `tools/`, `data/`, `.github/`

   **NAO suba** (se aparecerem): `config.yaml`, a pasta `logs/`, nem nenhuma
   pasta `__pycache__`.

8. Embaixo, clique no botao verde **Commit changes**.

---

## Parte 3 — Cadastrar os segredos (credenciais do Brevo)

1. No repositorio, va em **Settings** (aba do topo).
2. Menu esquerdo: **Secrets and variables > Actions**.
3. Clique em **New repository secret** e crie um por vez:

   | Name (exatamente assim) | Secret (valor)                                    |
   |-------------------------|---------------------------------------------------|
   | `SMTP_HOST`             | o servidor do Brevo, ex.: `smtp-relay.brevo.com`  |
   | `SMTP_PORT`             | `587`                                             |
   | `SMTP_USER`             | o **Login** mostrado na pagina SMTP do Brevo      |
   | `SMTP_PASSWORD`         | a **chave SMTP** que voce gerou                   |
   | `SMTP_FROM`             | o e-mail remetente **validado** no Brevo          |
   | `ALERT_TO`              | quem recebe os alertas, ex.: `voce@gmail.com`     |

   > `SMTP_FROM` precisa ser exatamente o remetente validado na Parte 1,
   > senao o Brevo recusa o envio. Para varios destinatarios em `ALERT_TO`,
   > separe por virgula.

---

## Parte 4 — Liberar a permissao de escrita do Actions

O programa salva o historico de precos de volta no repositorio.

1. Em **Settings > Actions > General**.
2. Em **Workflow permissions**, marque **Read and write permissions** > **Save**.

---

## Parte 5 — Rodar pela primeira vez (manual)

1. Aba **Actions** do repositorio.
2. Se pedir, clique em **I understand my workflows, go ahead and enable them**.
3. No menu esquerdo, clique em **Travel Monitor**.
4. A direita, **Run workflow > Run workflow**.
5. Aguarde ~2-4 min e clique na execucao para ver os logs.
   - Verde = rodou. Se houver alerta (preco abaixo do limite ou queda), o
     e-mail chega via Brevo.

> A primeira execucao so dispara alerta por "preco abaixo do limite"
> (ainda nao ha historico para comparar quedas).

---

## Parte 6 — Deixar automatico

Ja esta pronto. O `.github/workflows/monitor.yml` roda **todo dia as 09:00 UTC
(06:00 em Brasilia)**. Para mudar, edite a linha `cron` (sempre em UTC).

---

## Ajustar o que e monitorado

Edite `config.yaml.example` (no GitHub: abra o arquivo > icone de lapis >
edite > Commit). Mude rota, datas e o limite `max_price`.
- **ClickBus:** troque os *slugs* de origem/destino (pegue da URL apos fazer a
  busca no site).
- **Booking:** ajuste `city` (use `+` no lugar de espacos), datas e `max_price`
  (lembre: e o **total** da estadia).

---

## Problemas comuns

- **E-mail nao chegou:** confira que `SMTP_FROM` e o remetente validado no Brevo
  e que a chave SMTP foi colada certa. Veja os logs do Actions (so envia quando
  ha alerta de fato). Olhe tambem a aba **Logs/Transactional** no painel Brevo.
- **Booking sem precos nos logs:** o anti-bot do Booking pode bloquear o IP do
  GitHub Actions. Nesse caso, rode esse destino localmente ou foque no ClickBus.
- **O Actions parou de rodar sozinho:** repos sem atividade por 60 dias tem o
  cron pausado; entre e rode manual de novo para reativar.
