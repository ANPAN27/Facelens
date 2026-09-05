from abc import ABC, abstractmethod


class ReverseSearchProvider(ABC):
    @abstractmethod
    def search(self, image_path: str) -> list[dict]:
        pass

    @abstractmethod
    def name(self) -> str:
        pass
