from typing import Literal, Optional, TYPE_CHECKING, Type, cast
import logging
from pydantic import ConfigDict
from in_netsuite.rest import RestRequests
from abc import ABC
from in_netsuite.helpers import build_model
from in_netsuite.operators import Comparison, And, Operators
from in_netsuite.exceptions import MismatchConditionsError, InvalidNetSuiteResponseError
from in_netsuite.fields import FieldTypes, FieldInfo

logger = logging.getLogger("in_netsuite")

if TYPE_CHECKING:
    from in_netsuite.netsuite import NetSuiteItem, NetSuiteCollection


class JoinKeyPair:
    """
    Represents a key pair used for joining database tables or objects based on specific fields
    and join operations.

    This class facilitates the construction of join key information, which includes the base model,
    the fields to be joined, the type of join, and the direction of join. The class additionally
    provides properties and methods to help construct and represent the join statement.

    Attributes:
        base_key (NetSuiteFieldInfo): The field from the base model being joined.
        join_key (NetSuiteFieldInfo): The field from the comparison (joining) model.
        type (Literal["OUTER", "INNER", "CROSS"]): Represents the type of join operation.
        direction (Literal["LEFT", "RIGHT"]): Represents the direction of the join operation.
    """

    def __init__(
        self,
        join_operator: Comparison,
        base_model: Type["NetSuiteItem"],
        type_: Literal["OUTER", "INNER", "CROSS"],
        direction: Literal["LEFT", "RIGHT"],
    ):
        """
        A join key is in the format of (model, field, attributes)
        """

        if type(join_operator.compare) is not FieldInfo or type(join_operator.field) is not FieldInfo:
            raise ValueError(
                f"The join keys must be of type FieldInfo "
                f"{type(join_operator.compare)=} {type(join_operator.field)=}"
            )

        if base_model == join_operator.field.field_model:
            self.base_key: FieldInfo = join_operator.field
            self.join_key: FieldInfo = join_operator.compare
        else:
            self.base_key: FieldInfo = join_operator.compare
            self.join_key: FieldInfo = join_operator.field

        self.type = type_
        self.direction = direction

    def __repr__(self):
        return f"BaseKey({self.base_key}), JoinKey({self.join_key})"

    @property
    def base(self):
        return self.base_key

    @property
    def join(self):
        return self.join_key

    @property
    def join_statement(self):
        return f"{self.join.field_table}.{self.join.get_alias()} = {self.base.field_table}.{self.base.get_alias()}"


class _SuiteQLBase(RestRequests, ABC):
    """
    Base class for handling SuiteQL operations.

    This class provides a base for SuiteQL operations which facilitate the use of
    SuiteQL queries in interactions with NetSuite. It allows for defining models,
    collections, and other necessary elements required to construct and execute
    queries against the NetSuite system. It ensures compatibility with REST
    requests and provides foundational properties for handling SuiteQL-related
    features.

    Attributes:
        collection: An instance of the specified collection type, initialized
            during instantiation of the class.
        model: An instance of the model defined by the model_type attribute.
        column_fields: Tuple specifying the column fields to be used in SuiteQL
            queries.
        _response_model: Internal attribute to hold the response item model
            type, if provided. Defaults to None.
        query: Internal attribute to store the SuiteQL query string under
            construction. Defaults to None.
        _join_keys: Internal attribute representing a list of join key pairs for
            the query. Defaults to an empty list.
        _where_condition: Internal attribute to hold the where condition of the
            query. Defaults to None.
        _pydantic_config: Internal attribute to hold Pydantic configuration
            settings used for validation or processing. Defaults to None.
    """

    def __init__(
        self,
        collection: Type["NetSuiteCollection"],
        model: Type["NetSuiteItem"],
        column_fields: tuple[FieldInfo, ...] = None,
    ) -> None:
        self.response: Optional["NetSuiteCollection"] = None
        self.api_response: Optional[dict] = None
        self.collection = collection()  # Collection model that is being used
        self.model = model()  # Item model that is being used
        self.models: list[Type["NetSuiteItem"]] = [model]  # List of all the models that are being used
        self.column_fields: list[FieldInfo] = []
        self.query: Optional[str] = None
        self._response_model: Optional[Type["NetSuiteItem"]] = None
        self._join_keys: list[JoinKeyPair] = []
        self._where_condition: Optional[Operators] = None
        self._pydantic_config: Optional[ConfigDict] = None

        if len(column_fields) > 0:
            for input in column_fields:
                if type(input) is FieldInfo:
                    # Individual fields
                    self.column_fields.append(input)
                else:
                    # All the fields of the model
                    for name in input.model_fields:
                        self.column_fields.append(getattr(input, name))


class _SuiteQLJoin(_SuiteQLBase, ABC):
    """
    Represents SQL Join logic for SuiteQL queries.

    Provides methods to define and append join statements and their configurations.
    Utilized for constructing complex SQL queries within the SuiteQL framework. This
    class inherits from _SuiteQLBase and utilizes certain abstract functionalities
    provided by the ABC superclass.

    Attributes:
        _join_keys (list of JoinKeyPair): Stores join key configurations including the
            join statements, types, and directions associated with the given join.

    Methods:
        join: Adds a new join statement to the list of join configurations.
    """

    def join(
        self,
        join_statement: Comparison,
        type_: Literal["OUTER", "INNER", "CROSS"] = "OUTER",
        direction: Literal["LEFT", "RIGHT"] = "LEFT",
    ) -> "SuiteQLJoin":
        self._join_keys.append(JoinKeyPair(join_statement, type(self.model), type_, direction))

        # Adjust the class through the stages
        self.__class__ = SuiteQLJoin

        return cast("SuiteQLJoin", self)


class _SuiteQLWhere(_SuiteQLBase, ABC):
    """
    A specialized class for constructing WHERE clauses in SuiteQL queries.

    This class is a derived class used to build and handle logical WHERE conditions
    in SuiteQL queries. It processes conditions and operators to construct a valid
    WHERE clause for the query. Conditions must be homogeneous in type and adhere
    to the expected logical structure.
    """

    def where(self, *conditions: Operators) -> "SuiteQLWhere":
        if len({type(c) for c in conditions}) > 1:
            raise MismatchConditionsError("All conditions must be of the same type")

        if type(conditions[0]) is Comparison:
            self._where_condition = And(*conditions)
        elif len(conditions) > 1:
            raise MismatchConditionsError("You can only have one operator defined. Use nested operators instead")
        else:
            self._where_condition = conditions[0]

        # Adjust the class through the stages
        self.__class__ = SuiteQLWhere

        return cast("SuiteQLWhere", self)


class _SuiteQLExec(_SuiteQLBase, ABC):
    """
    A base class for executing SuiteQL queries with advanced configurations and model mappings.

    This class extends functionality for building and executing SuiteQL queries. It allows for
    customizable queries with join conditions, dynamic field mapping, and model validation
    based on Pydantic. It supports both simple and advanced queries, providing the mechanisms
    to structure, format, and validate query results dynamically.
    """

    async def all(self, extra: Literal["allow", "ignore", "forbid"] = "ignore") -> "SuiteQLResponse":

        return await self._exec(max_results=None, extra=extra)

    async def limit(
        self, limit: int = 1000, extra: Literal["allow", "ignore", "forbid"] = "ignore"
    ) -> "SuiteQLResponse":

        if limit > 1000:
            limit = 1000
            max_results = limit
        else:
            max_results = limit

        return await self._exec(limit=limit, max_results=max_results, extra=extra)

    async def first(self, extra: Literal["allow", "ignore", "forbid"] = "ignore") -> "SuiteQLResponse":

        return await self._exec(limit=1, max_results=1, extra=extra)

    async def one(self, extra: Literal["allow", "ignore", "forbid"] = "ignore") -> "SuiteQLResponse":
        response = await self._exec(limit=1, max_results=1, extra=extra)

        if response.has_more is True:
            raise InvalidNetSuiteResponseError("This search found more than one record")

        return response

    async def _exec(
        self,
        limit: int = 1000,
        max_results: Optional[int] = None,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> "SuiteQLResponse":

        self._pydantic_config = ConfigDict(extra=extra)

        self._construct_query()

        items = []
        offset = 0

        while True:
            self.api_response = await self.query_request(self.query, limit=limit, offset=offset)
            response = self._suiteql_model().model_validate(self._format_response(self.api_response))

            items.extend(response.items)
            offset += limit

            if response.has_more is False or (max_results is not None and offset >= max_results):
                if response.has_more is False:
                    response.offset = 0

                response.items = items
                response.count = len(items)
                self.response = response
                break

        # Adjust the class through the stages
        self.__class__ = SuiteQLResponse

        return cast("SuiteQLResponse", self)

    def _construct_query(self):
        select_statement = self._construct_select_and_model()

        self.query = f"SELECT {select_statement} FROM {self.model._instance.table}"

        if len(self._join_keys) > 0:
            self.query += (
                f" {self._join_keys[0].direction} {self._join_keys[0].type} "
                f"JOIN {self._join_keys[0].join.field_table} "
                f"ON {self._join_keys[0].join_statement}"
            )

        self._construct_where()

        if self._where_condition is not None:
            self.query += f" WHERE {str(self._where_condition)}"

    def _construct_where(self):
        literal_conditions = []
        for model in self.models:
            conditions = model.literal_field_conditions()
            if conditions is not None:
                literal_conditions.extend(conditions)

        if len(literal_conditions) > 0:
            if self._where_condition is not None:
                self._where_condition = And(self._where_condition, *literal_conditions).ql()
            else:
                if len(literal_conditions) == 1:
                    self._where_condition = literal_conditions[0].ql()
                else:
                    self._where_condition = And(*literal_conditions).ql()

        else:
            if self._where_condition is not None:
                self._where_condition = self._where_condition.ql()

    def _construct_select_and_model(self) -> str:
        select_statement: list = []
        dynamic_models = {}

        def add_column(table_, alias_):
            # If the select is a * we don't append any other columns to it
            if len(select_statement) == 0 or select_statement[0] != "*":
                select_statement.append(f'{table_} AS "{alias_}"')

        if len(self.column_fields) == 0 and len(self._join_keys) == 0 and self._pydantic_config.get("extra") == "allow":
            select_statement = ["*"]
            models = []

        else:
            models: list[tuple[Type[NetSuiteItem], Optional[JoinKeyPair]]] = [
                (key_pair.join.field_model, key_pair) for key_pair in reversed(self._join_keys)
            ]

        models.append((type(self.model), None))

        for model, key_pair in models:
            fields = {}

            for name, field in model.type_fields(FieldTypes.QL).items():
                if len(self.column_fields) != 0 and not self._column_match(model, name):
                    # Skip the column if it is not a match
                    continue

                # Base model fields
                if model is type(self.model):
                    # Skip the select for the join fields because they are added with the join model
                    if not self._field_is_join_table(name):
                        add_column(f"{field.field_table}.{field.get_alias(name)}", field.get_alias(name))
                    else:
                        # Nested models
                        field.annotation = dynamic_models[name]
                        field.default = ...  # Remove the default of None
                        field.default_factory = dynamic_models[name]  # Add a default factory

                # Join model
                else:
                    add_column(
                        f"{field.field_table}.{field.get_alias(name)}",
                        f"{key_pair.base.field_name}.{field.get_alias(name)}",
                    )

                # Add the field into the fields that we are going to use
                fields[name] = (field.annotation, field)

            # Base model
            if model is type(self.model):
                self._response_item_model = build_model(
                    model, self._pydantic_config, type_=FieldTypes.QL, fields=fields
                )
            else:
                self.models.append(model)  # Add this model to the list of consumed models
                dynamic_models[key_pair.base.field_name] = build_model(
                    model, self._pydantic_config, type_=FieldTypes.QL, fields=fields
                )

        return ", ".join(select_statement)

    def _column_match(self, model, field_name) -> bool:
        if self._field_is_join_table(field_name):
            return True
        for search_field in self.column_fields:
            # Return if the model and field match
            if search_field.field_model.__name__ == model.__name__ and search_field.field_name == field_name:
                return True
            # Return if the model is a subclass of the search model and the fields match
            elif issubclass(model, search_field.field_model) and search_field.field_name == field_name:
                return True
        return False

    def _field_is_join_table(self, field_name) -> bool:
        """
        Check if the field name is also the name of a join table
        """

        for key_pair in self._join_keys:
            if key_pair.base.field_name == field_name:
                return True
        return False

    def _suiteql_model(self) -> Type["NetSuiteCollection"]:
        """
        This will build a custom model to push for the SuiteQL response to map into. The alias field needs to be changed
        to lower case in order to match the model fields.
        """

        fields = {"items": list[self._response_item_model]}
        for name, field in type(self.collection).model_fields.items():
            if name not in fields:
                fields[name] = (field.annotation, field)

        return build_model(type(self.collection), self._pydantic_config, type_=FieldTypes.QL, fields=fields)

    @staticmethod
    def _format_response(response: dict) -> dict:
        """
        Maps the response into the correct format for the model to consume
        """
        items = response.pop("items")
        response["items"] = []

        for item in items:
            entry = {}
            for key, value in item.items():
                if "." in key:
                    key, attr = key.split(".")
                    if key not in entry:
                        entry[key] = {}
                    entry[key][attr] = value
                else:
                    entry[key] = value

            response["items"].append(entry)

        return response


class SuiteQLSelect(_SuiteQLJoin, _SuiteQLWhere, _SuiteQLExec): ...


class SuiteQLJoin(_SuiteQLWhere, _SuiteQLExec): ...


class SuiteQLWhere(_SuiteQLExec): ...


class SuiteQLResponse(_SuiteQLBase):
    @property
    def total_results(self) -> int:
        return self.__getattr__("total_results")

    @property
    def count(self) -> int:
        return self.__getattr__("count")

    @property
    def items(self) -> list["NetSuiteItem"]:
        return self.__getattr__("items")

    def __getattr__(self, item):
        if hasattr(self.response, item):
            return getattr(self.response, item)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")
