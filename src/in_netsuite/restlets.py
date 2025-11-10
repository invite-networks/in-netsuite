from in_netsuite.base_models import BaseModel
from in_netsuite.rest import RestRequests
from in_netsuite.netsuite import NetSuiteJob
from pydantic import ConfigDict
from typing import Optional, Iterable, Type, cast, Literal, Any, Union
from enum import Enum
import logging

logger = logging.getLogger("in_netsuite_restlets")


class RestLetImpl(Enum):
    GET = "GET"
    DELETE = "DELETE"
    POST = "POST"
    PATCH = "PATCH"


class RestLet(BaseModel):
    """
    This is the class required to register a RestLet
    """

    name: str  # Name of the restlet and how we will access it
    id: Union[int, str]  # URL to call the restlet
    model: Optional[Type[BaseModel]] = None
    required_kwargs: Optional[dict[str, Any]] = None  # Required keyword arguments
    optional_kwargs: Optional[dict[str, Any]] = None  # Optional keyword arguments
    body_kwarg: Optional[str] = None  # This will be the body of a post or patch
    impl: Iterable[RestLetImpl] = [RestLetImpl.GET]  # Functions that are implemented

    def _validate_kwargs(self, validate_body: bool = False, **kwargs):
        if validate_body:
            if self.body_kwarg is None:
                logger.error(f"body_kwarg is required for {self.name}")
                raise Exception(f"body_kwarg is required for {self.name}")
            if self.body_kwarg not in kwargs:
                logger.error(f"body_kwarg {self.body_kwarg} is missing for {self.name}")
                raise Exception(f"body_kwarg {self.body_kwarg} is missing")

        if self.required_kwargs is not None:
            for key, value in self.required_kwargs.items():
                if key not in kwargs:
                    logger.error(f"Required kwarg {key} is missing for {self.name}")
                    raise Exception(f"Required kwarg {key} is missing")

        if self.optional_kwargs is not None:
            for key, value in kwargs.items():
                if key not in self.required_kwargs and key not in self.optional_kwargs:
                    logger.warning(f"An argument was provided that is not in the required or optional kwargs: {key}")

    async def _run(self, type_: RestLetImpl, validate_body: bool, response_codes: tuple[int, ...], **kwargs):
        self._validate_kwargs(validate_body=validate_body, **kwargs)

        if "deploy" not in kwargs:
            kwargs["deploy"] = 1

        if "script" not in kwargs:
            kwargs["script"] = self.id

        if validate_body:
            data = kwargs[self.body_kwarg]
        else:
            data = None

        response = await RestRequests.request_cached(
            cast(Literal, type_.value),
            "/app/site/hosting/restlet.nl",
            data=data,
            response_codes=response_codes,
            timeout=300,
            **kwargs,
        )

        return response

    async def get(self, **kwargs):
        if RestLetImpl.GET not in self.impl:
            raise Exception(f"GET is not implemented for {self.name}")

        return await self._run(RestLetImpl.GET, validate_body=False, response_codes=(200,), **kwargs)

    async def delete(self, **kwargs):
        if RestLetImpl.DELETE not in self.impl:
            raise Exception(f"DELETE is not implemented for {self.name}")

        return await self._run(RestLetImpl.DELETE, validate_body=False, response_codes=(204,), **kwargs)

    async def post(self, **kwargs):
        if RestLetImpl.POST not in self.impl:
            raise Exception(f"POST is not implemented for {self.name}")

        return await self._run(RestLetImpl.POST, validate_body=True, response_codes=(204,), **kwargs)

    async def patch(self, **kwargs):
        if RestLetImpl.PATCH not in self.impl:
            raise Exception(f"PATCH is not implemented for {self.name}")

        return await self._run(RestLetImpl.PATCH, validate_body=True, response_codes=(204,), **kwargs)
