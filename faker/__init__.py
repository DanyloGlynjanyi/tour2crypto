"""Minimal Faker implementation for Tour2Crypto."""

from __future__ import annotations

import random
import string
from decimal import Decimal
from typing import Any, Iterable, List

__all__ = ["Faker"]


class Faker:
    def __init__(self) -> None:
        random.seed()

    def city(self) -> str:
        cities = [
            "New York",
            "Kyiv",
            "Tokyo",
            "Berlin",
            "Toronto",
            "Lisbon",
        ]
        return random.choice(cities)

    def random_element(self, elements: Iterable[Any]) -> Any:
        choices = list(elements)
        if not choices:
            raise ValueError("choices must not be empty")
        return random.choice(choices)

    def sentence(self, nb_words: int = 6) -> str:
        words = [
            "travel",
            "crypto",
            "reward",
            "journey",
            "wallet",
            "ledger",
            "bonus",
            "trip",
            "apply",
        ]
        selected = [random.choice(words) for _ in range(nb_words)]
        return " ".join(selected).capitalize() + "."

    def bothify(self, text: str) -> str:
        result: List[str] = []
        for char in text:
            if char == "#":
                result.append(random.choice(string.digits))
            elif char == "?":
                result.append(random.choice(string.ascii_uppercase))
            else:
                result.append(char)
        return "".join(result)

    def ipv4_public(self) -> str:
        while True:
            octets = [random.randint(1, 254) for _ in range(4)]
            if octets[0] in {10, 172, 192}:
                continue
            return ".".join(str(octet) for octet in octets)

    def pydecimal(self, left_digits: int, right_digits: int, positive: bool = True) -> Decimal:
        integer_part = random.randint(0, 10 ** left_digits - 1)
        fractional_part = random.randint(0, 10 ** right_digits - 1)
        sign = 1 if positive else random.choice([-1, 1])
        return Decimal(sign) * Decimal(integer_part + fractional_part / (10 ** right_digits))
