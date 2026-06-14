from abc import ABC, abstractmethod

import pandas as pd

class ET0Calculator(ABC):
    """
    Base class for ET0 (reference evapotranspiration) calculation.
    """

    registry: dict[str, type["ET0Calculator"]] = {}
    required_columns: tuple[str, ...] = ()
    min_rows: int = 1

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "__abstractmethods__", None):
            ET0Calculator.registry[cls.name()] = cls

    @classmethod
    @abstractmethod
    def name(cls):
        pass    

    @abstractmethod
    def calculate(self, data, **kwargs):
        pass

    def can_calculate(self, data: pd.DataFrame) -> bool:
        if len(data.index) < self.min_rows:
            return False
        if not self.required_columns:
            return True

        missing_cols = [column for column in self.required_columns if column not in data.columns]
        if missing_cols:
            return False

        required = data[list(self.required_columns)].apply(pd.to_numeric, errors="coerce")
        return not required.isna().any(axis=1).all()

    def get_calculator_by_name(name):
        return ET0Calculator.registry.get(name)

