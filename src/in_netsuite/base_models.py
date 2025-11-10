from pydantic import BaseModel as _BaseModel
from pydantic import RootModel as _RootModel
from pydantic import ConfigDict
from pydantic.fields import FieldInfo as PydanticFieldInfo
from pydantic._internal._model_construction import ModelMetaclass
from in_netsuite.operators import Comparison
from in_netsuite.fields import Field, FieldInfo, FieldTypes
from typing import Optional, TYPE_CHECKING, cast, Union, Type, Any, Literal, get_args
import json

if TYPE_CHECKING:
    from in_netsuite.netsuite import NetSuiteItem


def prettyprint(model: dict):
    return json.dumps(model, indent=4)


class ItemMetaClass(ModelMetaclass):
    """
    Metaclass that implements custom attribute access for models.

    This metaclass is used to define behavior for accessing attributes on model
    classes. It determines if the attribute corresponds to a field defined in the
    model and provides a custom class instance to represent such fields. If no such
    field is present, an AttributeError is raised to indicate that the attribute
    does not exist.
    """

    def __getattr__(self, item: str) -> FieldInfo:
        if item.startswith("_") or item == "model_fields":
            return super().__getattr__(item)
        if item in self.model_fields:
            return ItemBaseModel.standardize_field(
                self.model_fields.get(item), model=cast("type[NetSuiteItem]", self), name=item
            )
        return super().__getattr__(item)


class ItemBaseModel(_BaseModel, metaclass=ItemMetaClass):
    """
    Custom model with a custom metaclass for handling the FieldInfo of these models.
    """

    model_config = ConfigDict(populate_by_name=True)

    def prettyprint(self, *, exclude_none: bool = False):
        return prettyprint(self.model_dump(exclude_none=exclude_none))

    @staticmethod
    def standardize_field(
        field: Union[FieldInfo, PydanticFieldInfo], *, model: Type["NetSuiteItem"], name: str
    ) -> FieldInfo:
        """
        This will standardize the field to be a FieldInfo and make sure it has all the correct attributes.
        """
        if type(field) is PydanticFieldInfo:
            # Convert pydantic FieldInfo to ours
            return FieldInfo.from_pydantic_field_info(field, model=model, name=name)

        field.field_model = model
        field.field_name = name
        return field

    @classmethod
    def type_fields(cls, type_: FieldTypes) -> dict[str, FieldInfo]:
        """
        This will return all the fields for the specific type so we can build a model based on the type.
        Base fields and no field are included in any type.
        """
        return {
            name: cls.standardize_field(field, model=cast("type[NetSuiteItem]", cls), name=name).type_format(type_)
            for name, field in cls.model_fields.items()
            if (type(field) is PydanticFieldInfo or field.field_type == type_ or field.field_type == FieldTypes.Base)
        }

    @classmethod
    def literal_field_conditions(cls) -> Optional[tuple[Comparison, ...]]:
        """
        Returns the comparison operator for the literal fields.
        """
        conditions = tuple(
            cast(Comparison, field == get_args(field.annotation)[0])
            for field in cls.model_fields.values()
            if getattr(field.annotation, "__origin__", None) is Literal
        )
        return conditions or None

    def model_dump(self, *, type_: FieldTypes = FieldTypes.Rest, **kwargs) -> dict[str, Any]:
        kwargs["exclude"] = {
            name
            for name, field in self.__class__.model_fields.items()
            if hasattr(field, "field_type") and field.field_type not in {FieldTypes.Base, type_}
        }

        return super().model_dump(**kwargs)


class BaseModel(_BaseModel):
    """
    Represents a base model class with configuration settings and utility methods.

    This class extends from _BaseModel and provides additional configuration
    settings and functionality for enhanced model usage. It includes the ability
    to handle name population and extra attribute ignoring through its configuration.
    Furthermore, the class provides utility to pretty-print the model's data
    representation in JSON format.

    Attributes:
        model_config (ConfigDict): Configuration dictionary for the model.
            - 'populate_by_name': Boolean value specifying if fields
              should be populated by their alias.
            - 'extra': String value specifying how unknown extra attributes
              are handled. Set to "ignore" to silently discard them.

    Methods:
        prettyprint: Serializes the model into a pretty-printed JSON string.
    """

    model_config = ConfigDict(populate_by_name=True)

    def prettyprint(self, *, exclude_none: bool = False):
        return prettyprint(self.model_dump(exclude_none=exclude_none))


class RootModel(_RootModel):
    """
    Root model
    """

    def prettyprint(self):
        return json.dumps(self.model_dump(), indent=4)


class Link(BaseModel):
    """
    Links model
    """

    rel: str
    href: str


class Links(BaseModel):
    """
    Links model nested
    """

    links: list[Link]


class GenericRef(Links):
    """
    This is an item that returns an id ref_name
    """

    id: Optional[str] = None
    ref_name: Optional[str] = Field(default=None, alias="refName")
