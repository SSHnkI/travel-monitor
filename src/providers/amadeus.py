"""Provedor de VOOS usando a API Amadeus (Self-Service).

Tem um tier de teste GRATUITO. Cadastre-se em https://developers.amadeus.com,
crie um app e exporte as credenciais como variáveis de ambiente / secrets:

    AMADEUS_CLIENT_ID
    AMADEUS_CLIENT_SECRET

Este módulo serve como MODELO de provedor real:
- autentica (OAuth client_credentials)
- consulta ofertas
- normaliza tudo para a classe Offer

Se as credenciais não existirem, levanta RuntimeError (capturado pelo main,
que registra o erro e segue para o próximo destino).
"""
from __future__ import annotations

import os
from typing import Any

import requests

from ..logger import get_logger
from .base import Offer, Provider, register

log = get_logger(__name__)

_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


@register("amadeus")
class AmadeusProvider(Provider):
    kind = "flight"

    def _token(self) -> str:
        client_id = os.getenv("AMADEUS_CLIENT_ID")
        client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        if not (client_id and client_secret):
            raise RuntimeError(
                "Defina AMADEUS_CLIENT_ID e AMADEUS_CLIENT_SECRET para usar este provedor."
            )
        resp = requests.post(
            _AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def fetch_offers(self, params: dict[str, Any]) -> list[Offer]:
        token = self._token()
        query = {
            "originLocationCode": params["origin"],
            "destinationLocationCode": params["destination"],
            "departureDate": params["depart_date"],
            "adults": params.get("adults", 1),
            "currencyCode": params.get("currency", "BRL"),
            "max": params.get("max_results", 10),
        }
        if params.get("return_date"):
            query["returnDate"] = params["return_date"]

        resp = requests.get(
            _SEARCH_URL,
            headers={"Authorization": f"Bearer {token}"},
            params=query,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        offers: list[Offer] = []
        for item in data:
            price = float(item["price"]["grandTotal"])
            currency = item["price"].get("currency", "BRL")
            carriers = {
                seg["carrierCode"]
                for it in item.get("itineraries", [])
                for seg in it.get("segments", [])
            }
            offers.append(
                Offer(
                    price=price,
                    currency=currency,
                    details=f"{params['origin']}->{params['destination']} "
                    f"({', '.join(sorted(carriers))})",
                )
            )
        log.info("Amadeus retornou %d ofertas.", len(offers))
        return offers
