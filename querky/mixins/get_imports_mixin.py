class GetImportsMixin:
    def get_imports(self) -> set[str]:
        raise NotImplementedError()


__all__ = [
    "GetImportsMixin",
]
