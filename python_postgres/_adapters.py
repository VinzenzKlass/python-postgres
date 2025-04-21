from pydantic import BaseModel


class Values:
    values: list[BaseModel] | BaseModel

    def __init__(self, values: BaseModel | list[BaseModel]):
        self.values = values
