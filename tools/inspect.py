"""Inspetor de seletores de preço.

Abre uma URL com Playwright, procura elementos cujo texto pareça um preço
(R$, BRL, USD, etc.) e imprime seletores CSS candidatos para você colar no
campo 'price_selector' do config.yaml.

Uso:
    python tools/inspect.py "<URL>"
    python tools/inspect.py "<URL>" --wait-for "[data-testid='property-card']"
    python tools/inspect.py "<URL>" --no-headless        # abre o navegador visível
    python tools/inspect.py "<URL>" --regex "R\\$\\s*[0-9.]+,[0-9]{2}"

Pré-requisito:
    pip install playwright && python -m playwright install chromium
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

PRICE_RE_DEFAULT = r"(R\$|BRL|US\$|USD|€)\s?[0-9][0-9.\s]*,?[0-9]{0,2}"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _css_path(handle) -> str:
    """Gera um seletor CSS curto e estável para um elemento (via JS no browser)."""
    return handle.evaluate(
        """
        el => {
          function sel(node){
            if (!node || node.nodeType !== 1) return '';
            let s = node.tagName.toLowerCase();
            if (node.id) return s + '#' + CSS.escape(node.id);
            const cls = (node.getAttribute('class')||'')
              .trim().split(/\\s+/).filter(Boolean)
              .slice(0,2).map(c => '.' + CSS.escape(c)).join('');
            // prioriza data-testid se existir
            const tid = node.getAttribute('data-testid');
            if (tid) return s + "[data-testid='" + tid + "']";
            return s + cls;
          }
          return sel(el);
        }
        """
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Descobre seletores CSS de preço.")
    ap.add_argument("url")
    ap.add_argument("--wait-for", default=None, help="Seletor a aguardar.")
    ap.add_argument("--regex", default=PRICE_RE_DEFAULT, help="Regex de preço.")
    ap.add_argument("--wait-ms", type=int, default=3000)
    ap.add_argument("--no-headless", action="store_true")
    ap.add_argument("--top", type=int, default=15, help="Quantos seletores listar.")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright não instalado. Rode:\n"
              "  pip install playwright && python -m playwright install chromium")
        return 1

    price_re = re.compile(args.regex)
    counter: Counter[str] = Counter()
    samples: dict[str, str] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.no_headless, args=["--no-sandbox"])
        page = browser.new_context(user_agent=_UA, locale="pt-BR").new_page()
        print(f"Abrindo: {args.url}")
        page.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
        if args.wait_for:
            try:
                page.wait_for_selector(args.wait_for, timeout=30_000)
            except Exception:
                print(f"Aviso: '{args.wait_for}' não apareceu a tempo.")
        page.wait_for_timeout(args.wait_ms)

        # Pega os menores elementos que contêm um padrão de preço.
        elements = page.query_selector_all("span, div, p, strong, b")
        for el in elements:
            try:
                text = (el.inner_text() or "").strip()
            except Exception:
                continue
            if not text or len(text) > 40:
                continue
            if price_re.search(text):
                css = _css_path(el)
                if css:
                    counter[css] += 1
                    samples.setdefault(css, text)
        browser.close()

    if not counter:
        print("\nNenhum elemento de preço encontrado. Tente:")
        print("  - aumentar --wait-ms")
        print("  - passar --wait-for com um container da listagem")
        print("  - rodar com --no-headless para ver a página")
        return 2

    print(f"\nCandidatos a price_selector (top {args.top}):\n")
    for css, n in counter.most_common(args.top):
        print(f"  [{n:>3}x]  {css}")
        print(f"          exemplo: {samples[css]!r}")
    print("\nEscolha o seletor que aparece em quantidade parecida com o nº de")
    print("resultados da página e cole em 'price_selector' no config.yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
