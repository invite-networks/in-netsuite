from typing import Callable, TypeVar, ParamSpec, get_args, cast, TYPE_CHECKING, Type
from functools import wraps
from typing import Optional, Self
from pydantic.fields import FieldInfo as PydanticFieldInfo
from pydantic import Field as _Field
from enum import Enum
from in_netsuite.operators import Comparison
import logging

if TYPE_CHECKING:
    from in_netsuite.netsuite import NetSuiteItem


logger = logging.getLogger("in_netsuite_fields")

P = ParamSpec("P")
R = TypeVar("R")


class FieldTypes(Enum):
    Base = "Base"
    QL = "QL"
    Rest = "Rest"


class FieldInfo(PydanticFieldInfo):
    """
    This is a custom implementation of Pydantic's FieldInfo class. It allows us to use the fields in an ORM model as
    well as the standard way.
    """

    attr_prefix = "_attr_"  # This is used flag what should be extracted from the fields and added as class attrs

    def __eq__(self, compare) -> Comparison:
        return Comparison(self, compare, Comparison.Operator.EQ)

    def __ge__(self, compare) -> Comparison:
        return Comparison(self, compare, Comparison.Operator.GE)

    def __gt__(self, compare) -> Comparison:
        return Comparison(self, compare, Comparison.Operator.GT)

    def __le__(self, compare) -> Comparison:
        return Comparison(self, compare, Comparison.Operator.LE)

    def __lt__(self, compare) -> Comparison:
        return Comparison(self, compare, Comparison.Operator.LT)

    def __ne__(self, compare) -> Comparison:
        return Comparison(self, compare, Comparison.Operator.NE)

    def ___getattr__(self, item: str):
        nested_model = next(
            (t for t in get_args(self.annotation) if isinstance(t, type) and issubclass(t, NetSuiteItem)),
            None,
        )

        if nested_model is not None and item in nested_model.model_fields:
            field = nested_model.model_fields.get(item)
            field.field_model = cast("type[NetSuiteItem]", nested_model)
            field.field_name = item
            return field

        raise AttributeError(f"{self.__class__} has no attribute '{item}'")

    @property
    def field_type(self) -> FieldTypes:
        return getattr(self, f"{self.attr_prefix}field_type", None)

    @field_type.setter
    def field_type(self, value):
        if not hasattr(self, f"{self.attr_prefix}field_type"):
            setattr(self, f"{self.attr_prefix}field_type", value)

    @property
    def field_model(self) -> type["NetSuiteItem"]:
        return getattr(self, f"{self.attr_prefix}model", None)

    @field_model.setter
    def field_model(self, value):
        if not hasattr(self, f"{self.attr_prefix}model"):
            setattr(self, f"{self.attr_prefix}model", value)

    @property
    def field_name(self) -> str:
        return getattr(self, f"{self.attr_prefix}name", None)

    @field_name.setter
    def field_name(self, value):
        if not hasattr(self, f"{self.attr_prefix}name"):
            setattr(self, f"{self.attr_prefix}name", value)

    @property
    def field_table(self):
        if self.field_model is None:
            raise AttributeError("The model has not been set")

        return self.field_model()._instance.table if self.field_model is not None else None

    def type_format(self, type_: FieldTypes) -> Self:
        """
        This preps the field to be used for the type of request being performed
        """

        if type_ == FieldTypes.QL and self.json_schema_extra is not None:
            self.alias = self.json_schema_extra.get("alias_ql", self.alias)
        elif type_ == FieldTypes.Rest and self.json_schema_extra is not None:
            self.alias = self.json_schema_extra.get("alias_rest", self.alias)

        if self.alias is not None:
            if type_ == FieldTypes.QL:
                self.alias = self.alias.lower()

            self.serialization_alias = self.alias
            self.validation_alias = self.alias

        return self

    def get_alias(self, default: Optional[str] = None) -> str:
        """
        This returns the alias or the default
        """

        if self.alias is not None:
            return self.alias

        if default is not None:
            return default

        return self.field_name

    @classmethod
    def from_pydantic_field_info(
        cls,
        field: PydanticFieldInfo,
        *,
        model: Type["NetSuiteItem"],
        name: str,
    ) -> Self:

        kwargs = {slot: getattr(field, slot) for slot in field.__slots__}

        field_info = cls(**kwargs)
        field_info.field_model = model
        field_info.field_name = name
        field_info.field_type = FieldTypes.Base

        return field_info


def injection(func: Callable[P, R], type_: FieldTypes) -> Callable[P, R]:
    """
    This is used to allow us to have a custom field while still allowing all the type hints of pydantic's Field
    to work.
    """

    @wraps(func)
    def wrapper(default: P.args, **kwargs: P.kwargs) -> R:
        # Create a field using pydantic's Field
        pydantic_field = _Field(default=default, **kwargs)
        # Extract the attributes from pydantic to pass into our class
        field_info = FieldInfo(**{slot: getattr(pydantic_field, slot) for slot in pydantic_field.__slots__})
        field_info.field_type = type_
        return field_info

    return wrapper


"""
These are the custom fields available to use in the models
"""
Field = injection(_Field, FieldTypes.Base)
FieldQL = injection(_Field, FieldTypes.QL)
FieldRest = injection(_Field, FieldTypes.Rest)
