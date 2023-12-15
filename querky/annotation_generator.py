from abc import ABC, abstractmethod

from querky.base_types import TypeKnowledge


class AnnotationGenerator(ABC):
    @abstractmethod
    def generate(self, knowledge: TypeKnowledge, context: str) -> str:
        ...

    def annotate(self, knowledge: TypeKnowledge, context: str, force: bool = False) -> None:
        if knowledge.typehint is None or force:
            knowledge.typehint = self.generate(knowledge, context)
