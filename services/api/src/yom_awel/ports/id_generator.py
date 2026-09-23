from typing import Protocol
from uuid import UUID


class IDGenerator(Protocol):
    def generate(self) -> UUID: ...
