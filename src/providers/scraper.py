"""Provedor de WEB SCRAPING generico e configuravel (com suporte a Playwright).

Em vez de hardcodar cada site, este provedor e controlado pelo YAML: voce
informa a URL (com placeholders dos params), um seletor CSS que aponta para o
elemento de preco e uma regex para extrair o numero. Assim da para apontar para
varios sites sem escrever codigo novo.

Parametros aceitos em `params`:
  url            (obrigatorio) URL com {placeholders} preenchidos pelos params
  price_selector (obrigatorio) seletor CSS dos elementos de preco
  currency       moeda (padrao BRL)
  render_js      true = usa Playwright (sites com JS); false = requests
  wait_for       seletor CSS a aguardar antes de extrair (so com render_js)
  wait_ms        tempo extra de espera em ms (padrao 2000, so com render_js)
  price_regex    regex para extrair o numero do texto do elemento
  user_agent     User-Agent customizado
  block_assets   true (padrao) bloqueia imagens/fontes p/ acelerar (render_js)

LIMITACOES IMPORTANTES:
- Sites grandes (Google Flights, Booking, Skyscanner...) usam JS: render_js: true.
- Muitos tem anti-bot (Cloudflare/CAPTCHA) que pode bloquear o IP do CI.
- Seletores quebram quando o site muda o HTML -- por isso ficam no YAML.
- Respeite os Termos de Uso e o robots.txt. Use baixa frequencia.
- Use tools/inspect.py para descobrir o price_selector de cada site.
"""
from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from ..logger import get_logger
from .base import Offer, Provider, register

log = get_logger(__name__)

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_DEFAULT_PRICE_RE = r"(\d[\d.\s]*,?\d{0,2})"
_BLOCK_TYPES = {"image", "media", "font"}


def _to_float(text: str) -> float | None:
    """Converte texto de preco para float, lidando com formato BR e US.

    Exemplos: 'R$ 1.234,56' -> 1234.56 | 'R$ 1.093' -> 1093.0 |
              '229,89' -> 229.89 | '1234.56' -> 1234.56
    Regra: virgula sempre e separador decimal (BR). Quando ha apenas ponto,
    se o ultimo grupo tem 3 digitos tratamos como separador de milhar.
    """
    t = re.sub(r"[^0-9.,]", "", text.strip().replace("\xa0", " "))
    if not t:
        return None
    if "," in t:  # virgula = decimal (BR); ponto = milhar
        t = t.replace(".", "").replace(",", ".")
    elif "." in t:
        parts = t.split(".")
        if len(parts[-1]) == 3:  # ex.: 1.093 ou 1.093.456 -> milhar
            t = "".join(parts)
        # senao mantem como decimal (ex.: 1234.56)
    try:
        return float(t)
    except ValueError:
        return None


def _fetch_static(url: str, headers: dict[str, str]) -> str:
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def _fetch_rendered(url: str, params: dict[str, Any], headers: dict[str, str]) -> str:
    """Renderiza a pagina com JavaScript via Playwright (import tardio: opcional)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "render_js=true requer Playwright. Instale com:\n"
            "  pip install playwright && python -m playwright install chromium"
        ) from exc

    block_assets = bool(params.get("block_assets", True))
    wait_for = params.get("wait_for")
    wait_ms = int(params.get("wait_ms", 2000))

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        context = browser.new_context(
            user_agent=headers.get("User-Agent"),
            locale="pt-BR",
        )
        page = context.new_page()
        if block_assets:
            page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in _BLOCK_TYPES
                else route.continue_(),
            )
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if wait_for:
            try:
                page.wait_for_selector(wait_for, timeout=30000)
            except Exception:  # segue mesmo se nao aparecer; logamos depois
                log.warning("wait_for '%s' nao apareceu a tempo.", wait_for)
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
        return html


@register("scraper")
class ScraperProvider(Provider):
    kind = "generic"

    def fetch_offers(self, params: dict[str, Any]) -> list[Offer]:
        if "url" not in params or "price_selector" not in params:
            raise ValueError("scraper requer 'url' e 'price_selector' nos params.")

        try:
            url = params["url"].format(**params)
        except KeyError as exc:
            raise ValueError(f"Placeholder ausente na URL: {exc}") from exc

        ua = params.get("user_agent", _DEFAULT_UA)
        headers = {"User-Agent": ua}
        if params.get("render_js", False):
            html = _fetch_rendered(url, params, headers)
        else:
            html = _fetch_static(url, headers)

        soup = BeautifulSoup(html, "lxml")
        nodes = soup.select(params["price_selector"])
        if not nodes:
            log.warning(
                "Nenhum elemento casou com '%s' em %s. "
                "Verifique o seletor com tools/inspect.py.",
                params["price_selector"],
                url,
            )
            return []

        price_re = re.compile(params.get("price_regex", _DEFAULT_PRICE_RE))
        currency = params.get("currency", "BRL")

        offers: list[Offer] = []
        for node in nodes:
            text = node.get_text(" ", strip=True)
            match = price_re.search(text)
            if not match:
                continue
            value = _to_float(match.group(1))
            if value is not None and value > 0:
                offers.append(Offer(price=value, currency=currency, details=text[:80]))

        log.info("Scraper extraiu %d preco(s) de %s.", len(offers), url)
        return offers
