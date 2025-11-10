from typing import Literal, Optional, Union, TypeVar, Type, overload, Self, cast, Any
import httpx
import asyncio
import logging
from in_netsuite.rest import RestRequests
from in_netsuite.exceptions import InvalidNetSuiteResponseError, ConfigurationError, MismatchConditionsError
from pydantic import ConfigDict
from in_netsuite.suiteql import SuiteQLSelect
from in_netsuite.base_models import BaseModel, ItemBaseModel, Link, Links, GenericRef
from in_netsuite.fields import Field, FieldInfo, FieldTypes
from in_netsuite.helpers import build_model, extract_inner_class
from in_netsuite.operators import Operators, Comparison, And
from abc import ABC
from async_lru import alru_cache

logger = logging.getLogger("in_netsuite")


ItemType = TypeVar("ItemType", bound=ItemBaseModel)
Job = TypeVar("Job", bound="NetSuiteJob")


class _NetSuiteCommon(RestRequests):
    """
    Represents a base class that extends functionality related to settings, validation, and job execution
    in a NetSuite API interaction context.

    This class is built to provide utility methods to interact with settings attributes, perform validation,
    and handle asynchronous job operations. It can be used in scenarios where NetSuite entities and jobs
    require consistent handling of attributes and responses. It serves as a foundation for more specialized
    classes tailored to specific NetSuite entities.
    """

    @property
    def is_collection(self) -> bool:
        return isinstance(self, NetSuiteCollection)

    @property
    def is_item(self) -> bool:
        return isinstance(self, NetSuiteItem)


class NetSuiteCollection(BaseModel, _NetSuiteCommon, ABC):
    """
    Represents a collection of NetSuite records and provides methods for selecting, retrieving,
    and creating NetSuite objects.

    This class is designed to handle interactions with NetSuite APIs, facilitating operations
    such as fetching all records or single records, composing structured queries through
    column field selection, and creating new records with optional asynchronous handling.
    It utilizes validation and data modeling mechanisms for proper configuration and ensures
    seamless data management for both collections and individual records.
    """

    links: Optional[list[Link]] = None
    count: Optional[int] = None
    has_more: Optional[bool] = Field(None, alias="hasMore")
    offset: Optional[int] = None
    total_results: Optional[int] = Field(None, alias="totalResults")
    items: Optional[list[Union["GenericItem"]]] = Field(None)


class NetSuiteItem(ItemBaseModel, _NetSuiteCommon, ABC):
    """
    This class represents a NetSuite item model.

    The NetSuiteItem class provides functionality for managing records and their
    associated behaviors in the NetSuite system. It includes methods to determine the
    number of fields within a model, access table properties, update existing records in
    a detailed or asynchronous manner, delete specific records, and expand model fields
    based on particular configurations.

    Attributes:
        Model fields are dynamically inferred from the BaseModel implementation.
    """

    _instance: Optional["_Instance"]

    def __len__(self):
        return len(cast(dict, self.__class__.model_fields))

    def get_id(self) -> str:
        return getattr(self, "id")  # noqa: B009

    async def delete(self) -> httpx.Response:
        """
        Deletes a specific record
        """

        return await self._instance.delete(id_=self.get_id())

    @overload
    async def update(
        self,
        item: ItemType,
        *,
        async_: bool = False,
        poll=True,
        replace_selected_fields: bool = True,
        replace: Optional[str] = None,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> ItemType: ...

    @overload
    async def update(
        self,
        item: ItemType,
        *,
        async_: bool = False,
        poll=False,
        replace_selected_fields: bool = True,
        replace: Optional[str] = None,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> Job: ...

    async def update(
        self,
        item: ItemType,
        *,
        async_: bool = False,
        poll: bool = True,
        replace_selected_fields: bool = True,
        replace: Optional[str] = None,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> Union[Job, ItemType]:
        """
        Update an item
        """

        return await self._instance.update(
            id_=self.get_id(),
            item=item,
            async_=async_,
            poll=poll,
            replace_selected_fields=replace_selected_fields,
            replace=replace,
            extra=extra,
        )


class NetSuiteJob(_NetSuiteCommon):
    """
    NetSuiteJob class facilitates interaction with NetSuite jobs.

    Provides utilities for managing and polling jobs in NetSuite to monitor
    their statuses and retrieve results after completion. The class is designed
    for handling asynchronous operations and requires a valid job ID or URL
    to initialize. It uses predefined item types to validate results.

    Attributes:
        url (str): The URL used to perform job-related operations.

    Methods:
        poll(): Asynchronously polls the status of a job until it's completed
                and returns the generated object or result.
    """

    class JobStatus(BaseModel):
        id: Optional[str] = None
        links: Optional[list[Link]] = None
        completed: Optional[bool] = None
        progress: Optional[str] = None
        task: Optional[Links] = None

    def __init__(
        self,
        *,
        id_: str = None,
        url: str = None,
        instance: Optional["_RestInstance"] = None,
    ) -> None:
        if id_ is None and url is None:
            raise ValueError("You must provide either an id or a url to poll")

        if id_ is not None:
            self.url = f"/job/{id_}"
        else:
            self.url = url

        self.instance = instance

    @classmethod
    @overload
    async def run(
        cls,
        response: httpx.Response,
        poll: True,
        instance: "_RestInstance",
    ) -> ItemType: ...

    @classmethod
    @overload
    async def run(
        cls,
        response: httpx.Response,
        poll: False,
        instance: "_RestInstance",
    ) -> Self: ...

    @classmethod
    async def run(
        cls,
        *,
        response: httpx.Response,
        poll: bool,
        instance: Optional["_RestInstance"] = None,
    ) -> Union[ItemType, Self]:
        """
        This handles the response from an async job being created.
        """

        if response.status_code != 202:
            raise InvalidNetSuiteResponseError(
                f"We expected a 202 from NetSuite. " f"We received: {response.status_code} {response.text}"
            )

        job = cls(url=response.headers.get("location"), instance=instance)

        if poll is True:
            return await job.poll()

        return job

    async def poll(self) -> ItemType:
        """
        Pull a job until it is complete and return the newly created object
        """

        sleep = 1

        while True:
            response = await self.request("GET", self.url)

            job_status = self.JobStatus.model_validate(response.json())
            if job_status.completed is True:
                logger.debug(f"Job completed: {job_status.id}. Getting the results of the task")
                response = await self.request("GET", f"{self.url}/task/{job_status.id}/result", response_codes=(204,))

                if self.instance is not None:
                    return await self.instance.retrieve_fresh(response)

            logger.debug(f"Waiting on job to complete. Sleeping for {sleep}")
            await asyncio.sleep(sleep)
            if sleep < 4:
                sleep = sleep * 2


class _BaseInstance(RestRequests, ABC):
    def __init__(self, collection: Type[NetSuiteCollection]):
        self.collection = collection
        self.model = cast(Type[NetSuiteItem], extract_inner_class(self.collection.model_fields.get("items").annotation))
        self.model_config = ConfigDict(populate_by_name=True)

    @property
    def model(self) -> Type[NetSuiteItem]:
        return self._model

    @model.setter
    def model(self, model: Type[NetSuiteItem]):
        # if not issubclass(NetSuiteItem, model):
        #    raise ValueError("The model must be a subclass of NetSuiteItem")
        self._model = model
        self._model._instance = cast(_Instance, self)

    @property
    def _base_model(self):
        return next(prev for prev, curr in zip(self.model.__mro__, self.model.__mro__[1:]) if curr is NetSuiteItem)

    def get_attr(self, item: str) -> Any:
        """
        This returns the attribute from the Settings class if they exist or attributes from the model
        """

        if hasattr(self.model, "Settings") and hasattr(self.model.Settings, item):
            return getattr(self.model.Settings, item)

        if hasattr(self.model, item):
            return getattr(self.model, item)

        return None

    def validate_attr(self, item: str):
        """
        This validates the attribute exists in the Settings class. If it doesn't then it raises an error.
        """

        value = self.get_attr(item)

        if value is None:
            raise ConfigurationError(f"You must define '{item}' in the Settings class of {self.model.__name__}")

        return value

    @property
    def table(self):
        raise AttributeError("Table is not defined for this collection")

    @property
    def url(self):
        raise AttributeError("Url is not defined for this collection")


class _QLInstance(_BaseInstance):
    def select(self, *column_fields: Union[FieldInfo, Type["NetSuiteItem"]]) -> SuiteQLSelect:
        return SuiteQLSelect(self.collection, self.model, column_fields=column_fields)

    @property
    def table(self):
        return self.get_attr("table") or f"{self._base_model.__name__.lower()}"


class _RestInstance(_BaseInstance):
    @property
    def url(self):
        return self.get_attr("url") or f"/{self._base_model.__name__.lower()}"

    @alru_cache(maxsize=10000, ttl=300)
    async def get(
        self,
        id_: str,
        *,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> ItemType:
        """
        Returns the data for all the records or a single record based on the id
        """

        headers = {"Prefer": "return=representation", "Accept": "application/json"}

        self.model_config["extra"] = extra

        model = build_model(self.model, self.model_config, type_=FieldTypes.Rest)
        response = await self.get_request(f"{self.url}/{id_}", headers=headers)

        #try:
        #    model.model_validate(response.json())
        #except Exception as e:
        #    print("HERE1", e, response.json())

        return model.model_validate(response.json())

    @overload
    async def transform(
        self,
        customer_id: str,
        item: ItemType,
        *,
        async_: bool = False,
        poll: Literal[True],
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> ItemType: ...

    @overload
    async def transform(
        self,
        customer_id: str,
        item: ItemType,
        *,
        async_: bool = False,
        poll: Literal[False],
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> NetSuiteJob: ...

    async def transform(
        self,
        customer_id: str,
        item: ItemType,
        *,
        async_: bool = False,
        poll=True,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> Union[ItemType, NetSuiteJob]:
        """
        Automates the creation of related records
        """
        return await self.create(item, async_=async_, poll=poll, extra=extra, url=f"/customer/{customer_id}/!transform{self.url}")


    async def follow(self, url: str):
        """
        Pass in a url from a response
        """
        headers = {"Prefer": "return=representation", "Accept": "application/json"}

        return await self.get_request(url, headers=headers)

    class Find:
        def __init__(self, instance: "_RestInstance", *conditions: Operators):
            self.instance = instance
            self.conditions = conditions

        async def one(
            self, *, extra: Literal["allow", "ignore", "forbid"] = "ignore", expand: bool = False
        ) -> Union[ItemType, "GenericItem", type(None)]:
            collection = await self._exec(limit=1)
            if collection.count == 0:
                return None
            elif collection.has_more is True:
                raise InvalidNetSuiteResponseError("This search found more than one record")

            if expand is True:
                return await self.instance.get(collection.items[0].id, extra=extra)

            return collection.items[0]

        async def all(self) -> NetSuiteCollection:
            limit = 1000
            offset = 0
            items = []

            while True:
                response = await self._exec(limit=limit, offset=offset)
                items.extend(response.items)
                offset += limit

                if response.has_more is False:
                    response.items = items
                    response.offset = 0
                    response.count = len(items)
                    return response

        async def _exec(self, *, limit: int = 1000, offset: int = 0) -> NetSuiteCollection:
            headers = {"Prefer": "return=representation", "Accept": "application/json"}

            kwargs = {
                "limit": limit,
                "offset": offset,
            }

            if self.conditions:
                if len({type(c) for c in self.conditions}) > 1:
                    raise MismatchConditionsError("All conditions must be of the same type")
                if type(self.conditions[0]) is Comparison:
                    query = And(*self.conditions).rest()
                elif len(self.conditions) > 1:
                    raise MismatchConditionsError(
                        "You can only have one operator defined. Use nested operators instead"
                    )
                else:
                    query = self.conditions[0].rest()
                kwargs["q"] = query

            # model = build_model(self.instance.collection, self.instance.model_config, type_=FieldTypes.Rest)
            response = await self.instance.get_request(f"{self.instance.url}", headers=headers, **kwargs)
            return NetSuiteCollection.model_validate(response.json())

    def find(
        self,
        *conditions: Operators,
    ) -> Find:
        return self.Find(self, *conditions)

    @overload
    async def create(
        self,
        item: ItemType,
        *,
        async_: bool = False,
        poll: Literal[True],
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
        url: str = None,
    ) -> ItemType: ...

    @overload
    async def create(
        self,
        item: ItemType,
        *,
        async_: bool = False,
        poll: Literal[False],
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
        url: str = None,
    ) -> NetSuiteJob: ...

    async def create(
        self,
        item: ItemType,
        *,
        async_: bool = False,
        poll=True,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
        url: str = None,
    ) -> Union[ItemType, NetSuiteJob]:
        """
        Create an instance of an item
        """

        self.model_config["extra"] = extra

        if async_ is True:
            headers = {"Prefer": "respond-async"}
            response_codes = (202,)
        else:
            headers = {}
            response_codes = (204,)

        #print("HERE")
        #print(item.model_dump(exclude_none=True, by_alias=True, mode="json"))

        if url is None:
            url = self.url

        response = await self.request(
            type_="POST",
            url=url,
            data=item.model_dump(exclude_none=True, by_alias=True, mode="json"),
            response_codes=response_codes,
            headers=headers,
        )

        if response.status_code == 204:
            return await self.retrieve_fresh(response)

        return await NetSuiteJob.run(response=response, poll=poll, instance=self)

    async def delete(self, id_: str) -> httpx.Response:
        """
        Deletes a specific record
        """

        return await self.delete_request(f"{self.url}/{id_}")

    @overload
    async def update(
        self,
        id_: str,
        item: ItemType,
        *,
        async_: bool = False,
        poll=True,
        replace_selected_fields: bool = True,
        replace: Optional[str] = None,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> ItemType: ...

    @overload
    async def update(
        self,
        id_: str,
        item: ItemType,
        *,
        async_: bool = False,
        poll=False,
        replace_selected_fields: bool = True,
        replace: Optional[str] = None,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> Job: ...

    async def update(
        self,
        id_: str,
        item: ItemType,
        *,
        async_: bool = False,
        poll: bool = True,
        replace_selected_fields: bool = True,
        replace: Optional[str] = None,
        extra: Literal["allow", "ignore", "forbid"] = "ignore",
    ) -> Union[Job, ItemType]:
        """
        Update an item
        """

        self.model_config["extra"] = extra

        if async_ is True:
            headers = {"Prefer": "respond-async"}
            response_codes = (202,)
        else:
            headers = {}
            response_codes = (204,)

        # Determine the replace fields
        if replace_selected_fields is True:
            if replace is None:
                if hasattr(self.model, "item"):
                    replace = "item"
                elif hasattr(self.model, "line"):
                    replace = "line"
                else:
                    raise ValueError(f"We can not determine the replace value {self.model.__name__}")
            elif not hasattr(self, replace):
                raise ValueError(f"'{replace}' is not a valid replace value for {self.model.__name__}")

        response = await self.request(
            type_="PATCH",
            url=f"{self.url}/{id_}",
            data=item.model_dump(exclude_none=True, by_alias=True, mode="json"),
            response_codes=response_codes,
            headers=headers,
            replaceSelectedFields=replace_selected_fields,
            replace=replace,
        )

        if response.status_code == 204:
            return await self.retrieve_fresh(response)

        return await NetSuiteJob.run(
            response=response,
            poll=poll,
            instance=self,
        )

    async def retrieve_fresh(self, response: httpx.Response) -> Optional[ItemType]:
        """
        This will retrieve the url from the response, invalidate the cache and return the fresh data
        """
        url = response.headers.get("location")
        id_ = url.rstrip("/").split("/")[-1]
        self.get.cache_invalidate(id_, extra=self.model_config.get("extra"))

        if id_ == "0":
            # There is no result that is passed back if the ID is 0
            return None

        response = await self.get_request(url)

        #try:
        #    self.model.model_validate(response.json())
        #except Exception as e:
        #    print("HERE2", e, response.json())

        return self.model.model_validate(response.json())


class GenericItem(NetSuiteItem, GenericRef, Links):
    """
    This is any item that returns an id ref_name and a link
    """


class _Instance(_QLInstance, _RestInstance): ...
