from typing import TYPE_CHECKING, Union, Any
from abc import ABC, abstractmethod
from enum import Enum
from datetime import date
import logging

if TYPE_CHECKING:
    from in_netsuite.fields import FieldInfo

logger = logging.getLogger("in_netsuite_operators")


class _Expression(ABC):
    """
    Abstract base class for creating custom expression objects.

    Represents a base structure for defining expressions with a string
    representation. It serves as a foundation for subclasses to implement
    concrete behavior for specific types of expressions.
    """

    @abstractmethod
    def __str__(self) -> str: ...


class Comparison(_Expression):
    """
    Represents a comparison expression for use in queries.

    This class is used to construct comparison expressions involving a specific
    field, a value to compare, and a comparison operator. These expressions are
    intended to be used in query construction, providing string representation
    suitable for readability and debugging purposes.
    """

    class OperatorContext(Enum):
        Rest = "rest"  # https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1545222128.html
        QL = "ql"

    class Operator(Enum):
        EQ = "eq"
        NE = "ne"
        GT = "gt"
        GE = "ge"
        LT = "lt"
        LE = "le"
        Contains = "contains"
        StartsWith = "startswith"
        EndsWith = "endswith"
        Like = "like"

    CompOperators = {
        OperatorContext.Rest: {
            type(None): {
                Operator.EQ: "EMPTY",
                Operator.NE: "EMPTY_NOT",
            },
            str: {
                Operator.EQ: "IS",
                Operator.NE: "IS_NOT",
                Operator.StartsWith: "START_WITH",
                Operator.EndsWith: "END_WITH",
                Operator.Contains: "CONTAIN",
            },
            bool: {
                Operator.EQ: "IS",
                Operator.NE: "IS_NOT",
            },
            date: {
                Operator.EQ: "ON",
                Operator.NE: "ON_NOT",
                Operator.GT: "AFTER",
                Operator.GE: "ON_OR_AFTER",
                Operator.LT: "BEFORE",
                Operator.LE: "ON_OR_BEFORE",
            },
            Operator.EQ: "EQUAL",
            Operator.NE: "EQUAL_NOT",
        },
        OperatorContext.QL: {
            Operator.EQ: "=",
            Operator.NE: "!=",
            Operator.GT: ">",
            Operator.GE: ">=",
            Operator.LT: "<",
            Operator.LE: "<=",
            Operator.Like: "LIKE",
        },
    }

    def __init__(self, field: "FieldInfo", compare: Any, operator: Operator) -> None:
        self.field = field
        self.compare = compare
        self.operator = operator

    def get_operator(self, context: OperatorContext) -> str:
        # Type specific first
        operator = self.CompOperators.get(context, {}).get(type(self.compare), {}).get(self.operator, None)

        # Context specific second
        if operator is None:
            operator = self.CompOperators.get(context, {}).get(self.operator, None)

        if operator is None:
            raise ValueError(f"Invalid operator {self.operator} for context {context}")

        logger.debug(f"Selected {operator=} for {type(self.compare)} and {context=}")

        return operator

    def __repr__(self):
        return (
            f"{self.field.get_alias(self.field.field_name)} "
            f"{self.get_operator(self.OperatorContext.QL)} '{self.compare}'"
        )

    def __str__(self):
        return self.__repr__()

    def ql(self):
        if type(self.compare) is date:
            return (
                f"{self.field.field_table}.{self.field.get_alias(self.field.field_name)} "
                f"{self.get_operator(self.OperatorContext.QL)} '{self.compare.strftime("%-m/%-d/%Y")}'"
            )
        return (
            f"{self.field.field_table}.{self.field.get_alias(self.field.field_name)} "
            f"{self.get_operator(self.OperatorContext.QL)} '{self.compare}'"
        )

    def rest(self):
        operator = self.get_operator(self.OperatorContext.Rest)

        # Exclude the compare value
        if operator == "EMPTY" or operator == "EMPTY_NOT":
            return f"{self.field.get_alias(self.field.field_name)} {operator}"

        elif type(self.compare) is date:
            return f'{self.field.get_alias(self.field.field_name)} {operator} "{self.compare.strftime("%-m/%-d/%Y")}"'

        return f'{self.field.get_alias(self.field.field_name)} {operator} "{self.compare}"'


class _Expression(_Expression, ABC):
    """
    Represents an abstract base class for expressions.

    This class serves as a foundation for creating expressions by combining multiple
    comparison objects. It provides a mechanism to format these expressions as strings
    with a specified operator and ensures that subclasses define their operator.

    Attributes:
    fields (tuple): A tuple containing comparison objects, representing
        individual components of the expression.

    Methods:
    operator: An abstract property that must be implemented by subclasses to
        define the operator used between comparison objects.
    """

    def __init__(self, *fields: Comparison) -> None:
        self.fields = fields

    def __str__(self):
        return f" {self.operator} ".join([f"({field})" for field in self.fields])

    def ql(self):
        return f" {self.operator} ".join([f"({field.ql()})" for field in self.fields])

    def rest(self):
        return f" {self.operator} ".join([f"({field.rest()})" for field in self.fields])

    @property
    @abstractmethod
    def operator(self) -> str: ...


class And(_Expression):
    """
    Logical AND expression.

    Represents a logical AND operation as part of an expression tree or other
    boolean logic structure. This class is typically used in contexts requiring
    evaluation or construction of composite boolean expressions.

    Attributes:
    operator : str
        The logical operator used by this class, which is set to "AND".
    """

    operator = "AND"


class Or(_Expression):
    """
    Represents a logical OR operation in a conditional expression.

    This class defines the properties and behavior associated with a logical OR
    operator in the context of expressions. It is used to combine multiple
    conditions where at least one condition must evaluate to true.

    Attributes:
    operator: str
        The string representation of the logical operator, which is "OR"
        for this class.
    """

    operator = "OR"


Operators = Union[Comparison, And, Or]
