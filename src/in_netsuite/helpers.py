from typing import Optional, TYPE_CHECKING, Type, Union, cast, overload, Any, get_args
from pydantic import ConfigDict, create_model, PrivateAttr
from in_netsuite.fields import FieldTypes

if TYPE_CHECKING:
    from in_netsuite.netsuite import NetSuiteItem, NetSuiteCollection


def get_alias(name, field) -> str:
    """
    Return the alias for a given field or the field name in lowercase.

    This function determines the alias for a given field. If the alias
    is specified for the field, it returns the alias converted to
    lowercase. Otherwise, it returns the name parameter as lowercase.

    Args:
        name: str
            The name of the field.
        field: object
            An object representing the field, which must have an
            'alias' attribute.

    Returns:
        str: The alias if it exists, or the field name in lowercase.
    """
    if field.alias is not None:
        return field.alias
    return name


def extract_inner_class(annotation: Any) -> type:
    """
    Given an annotation like Optional[List[Vendor]], return the Vendor class.
    """
    args = get_args(annotation)
    if not args:
        return (
            annotation
            if isinstance(annotation, type)
            else ValueError(f"Could not extract model from annotation: {annotation}")
        )

    for arg in args:
        result = extract_inner_class(arg)
        if result:
            return result
    raise ValueError(f"Could not extract model from annotation: {annotation}")


@overload
def build_model(
    model: Type["NetSuiteItem"],
    config: ConfigDict,
    *,
    type_: FieldTypes,
    fields: Optional[dict] = None,
) -> Type["NetSuiteItem"]:
    """
    build_model(model, config, *, type_, fields=None)

    Builds and configures a NetSuiteItem model with the provided configuration and
    settings.

    Parameters:
    model : Type[NetSuiteItem]
        The NetSuiteItem model class to be built.
    config : ConfigDict
        Configuration dictionary containing the settings for the model.
    type_ : Literal['Rest', 'QL']
        Specifies the type of the model. Accepted values are "Rest" or "QL".
    fields : dict, optional
        A dictionary specifying the fields for the model. Defaults to None.

    Returns:
    Type[NetSuiteItem]
        The configured NetSuiteItem model type.

    Raises:
    KeyError
        If required configuration keys are missing from the provided config.
    TypeError
        If the provided fields parameter is not a dictionary when specified.
    """
    ...


@overload
def build_model(
    model: Type["NetSuiteCollection"],
    config: ConfigDict,
    *,
    type_: FieldTypes,
    fields: Optional[dict] = None,
) -> Type["NetSuiteCollection"]:
    """
    Builds and returns a configured model instance of the specified type.

    This function is a utility for creating an instance of the given `NetSuiteCollection`
    model class type, with configurations defined by the provided configuration dictionary
    and additional parameters. It supports different types of collection models as
    specified by the `type_` parameter and optionally allows customization of the model
    via the `fields` parameter. The output is tailored to the selected `type_`, providing
    the needed functionality as per the input.

    Arguments:
        model (Type[NetSuiteCollection]): The model class type to be instantiated.
        config (ConfigDict): Configuration dictionary including key-value pairs relevant
            to the model's initialization.
        type_ (Literal["Rest", "QL"]): Specifies the type of collection model to build.
            It supports only "Rest" and "QL" types.
        fields (Optional[dict]): An optional dictionary to customize or map fields for
            the model instance constructed.

    Returns:
        Type[NetSuiteCollection]: A configured instance of the provided model type.

    Raises:
        ValueError: If the provided `type_` parameter is not "Rest" or "QL".
        TypeError: If `fields` is provided but is not a dictionary.
    """
    ...


def build_model(
    model: Union[Type["NetSuiteItem"], Type["NetSuiteCollection"]],
    config: ConfigDict,
    *,
    type_: FieldTypes,
    fields: Optional[dict] = None,
) -> Union[Type["NetSuiteItem"], Type["NetSuiteCollection"]]:
    """
    Construct a BaseModel subclass dynamically based on the provided model, type, and fields.

    Parameters:
        model (Union[Type["NetSuiteItem"], Type["NetSuiteCollection"]]): Defines
            the base model type to be used for constructing the new model.
        config (ConfigDict): A dictionary containing configuration options
            for the dynamic model.
        type_ (Literal["Rest", "QL"]): Specifies the operational type of the
            model being created, such as "Rest" or "QL".
        fields (Optional[dict], optional): Dictionary mapping field names to
            their attributes, such as types or metadata. Defaults to None.

    Returns:
        Type[BaseModel]: A dynamically created subclass of BaseModel tailored
        as per the provided parameters and field details.
    """
    from in_netsuite.netsuite import NetSuiteItem, NetSuiteCollection

    if issubclass(model, NetSuiteItem):
        base = NetSuiteItem
    elif issubclass(model, NetSuiteCollection):
        base = NetSuiteCollection
    else:
        raise ValueError(f"Model '{model}' must be a subclass of either NetSuiteItem or NetSuiteCollection")

    if fields is None:
        if hasattr(model, "type_fields"):
            fields = {name: (field.annotation, field) for name, field in model.type_fields(type_).items()}
        else:
            fields = {name: (field.annotation, field) for name, field in model.model_fields.items()}

    dynamic_model = create_model(
        f"{model.__name__}{type_.name}",
        __base__=base,
        __module__=model.__module__,
        __cls_kwargs__=cast(dict, config),
        **fields,
    )

    # Copy any private attributes to the new model
    dynamic_model.__private_attributes__ = {
        name: PrivateAttr(getattr(model, name)) for name in model.__private_attributes__
    }

    return dynamic_model
