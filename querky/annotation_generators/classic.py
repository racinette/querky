from querky.annotation_generator import AnnotationGenerator
from querky.base_types import TypeKnowledge
from querky.common_imports import TYPING


class ClassicAnnotationGenerator(AnnotationGenerator):
    def __init__(self, new_style_typehints: bool):
        self.new_style_typehints = new_style_typehints

    def generate(self, knowledge: TypeKnowledge, context: str) -> str:
        typename = knowledge.metadata.counterpart

        if knowledge.is_array:
            if self.new_style_typehints:
                if knowledge.elem_is_optional:
                    typename = f"list[{typename} | None]"
                else:
                    typename = f"list[{typename}]"
            else:
                if knowledge.elem_is_optional:
                    typename = f"typing.List[typing.Optional[{typename}]]"
                else:
                    typename = f"typing.List[{typename}]"
                knowledge.add_import(TYPING)

        if knowledge.is_optional:
            if self.new_style_typehints:
                typename = f"{typename} | None"
            else:
                typename = f"typing.Optional[{typename}]"
                knowledge.add_import(TYPING)

        return typename
