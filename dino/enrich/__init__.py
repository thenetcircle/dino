from abc import ABC


class IEnrichmentManager(ABC):
    def handle(self, data: dict) -> dict:
        raise NotImplementedError()


class IEnricher(ABC):
    def __call__(self, *args, **kwargs) -> dict:
        raise NotImplementedError()
