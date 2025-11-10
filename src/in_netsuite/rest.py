from typing import Literal, Optional, TYPE_CHECKING, Type
import httpx
import asyncio
import json
import logging
import oauthlib.oauth1
from urllib.parse import urlencode, quote
from in_netsuite.exceptions import NetSuiteResponseError, DoesNotExistError, NetSuiteDataChangedError
from async_lru import alru_cache

logger = logging.getLogger("in_netsuite_rest")

if TYPE_CHECKING:
    from in_netsuite import NetSuite


class RestRequests:
    _netsuite: Type["NetSuite"]  # Reference to the credentials

    @classmethod
    def init(cls, netsuite: Type["NetSuite"]):
        """
        Initialize the class with credentials
        """
        cls._netsuite = netsuite

    @classmethod
    @alru_cache(maxsize=1000, ttl=600)
    async def request_cached(cls, *args, **kwargs):
        return await cls.request(*args, **kwargs)

    @classmethod
    async def request(
        cls,
        type_: Literal["GET", "POST", "PATCH", "PUT", "DELETE"],
        url,
        data: Optional[dict] = None,
        *,
        response_codes: tuple[int, ...] = (200,),
        headers: Optional[dict] = None,
        sleep: int = 1,
        timeout=60,
        **kwargs,
    ) -> httpx.Response:
        """
        This makes the request to the server. It will handle the rate limiting and async requests and the auth headers.
        Args:
            type_: Type of request
            url: URL to make the request to
            data: Data to send in a post
            response_codes: Valid response codes to return from the server.
            headers: Headers to send
            sleep: Sleep time
            timeout: Timeout for the request
            kwargs: Additional arguments added to the query string
        """

        oath_client = oauthlib.oauth1.Client(
            client_key=cls._netsuite.client_id,
            client_secret=cls._netsuite.client_secret,
            resource_owner_key=cls._netsuite.token_id,
            resource_owner_secret=cls._netsuite.token_secret,
            realm=cls._netsuite.realm,
            signature_method="HMAC-SHA256",
        )

        url = cls._format_url(url, **kwargs)

        # Convert the data to json so we can sign it
        if data is not None:
            data = json.dumps(data)

        async with httpx.AsyncClient(timeout=timeout) as client:
            action = getattr(client, type_.lower())
            url, oath_headers, body = oath_client.sign(url, http_method=type_, body=data)

            # Add the additional headers to the oauth headers
            oath_headers.update({k: v.encode("utf-8") for k, v in headers.items()}) if headers else None

            logger.debug(f"Performing '{type_}' request to {url}")

            if type_ == "GET" or type_ == "DELETE":
                response = await action(url, headers=oath_headers)
            elif type_ == "POST" or type_ == "PATCH" or type_ == "PUT":
                response = await action(url, headers=oath_headers, content=data)
            else:
                raise NotImplementedError(f"Type {type_} not implemented")

            # Rate limit handling
            if response.status_code == 429:
                # We exceeded the rate limit, and we are going to start backing off
                logger.warning(f"Sleeping for {sleep} Rate limited: {response.text}")
                await asyncio.sleep(sleep)
                return await cls.request(type_, url, data, headers=headers, sleep=sleep * 2, **kwargs)

            if response.status_code not in response_codes:
                try:
                    error_details = response.json()
                except json.decoder.JSONDecodeError:
                    error_details = f"{response.status_code}: {response.text}"

                if response.status_code == 400:
                    if (
                        next(
                            (
                                error
                                for error in error_details["o:errorDetails"]
                                if "Record has been changed" in error.get("detail", "")
                            ),
                            None,
                        )
                        is not None
                    ):
                        raise NetSuiteDataChangedError(f"Record has been changed: {error_details}")

                raise NetSuiteResponseError(f"Failed to make request: {error_details} url={url}")

            return response

    @classmethod
    def _base_url(cls, api: Literal["restlet", "rest"] = "rest"):
        """
        Return the base url
        :return:
        """

        if api == "rest":
            return f"https://{cls._netsuite.account_id}.suitetalk.api.netsuite.com/services/rest"
        elif api == "restlet":
            return f"https://{cls._netsuite.account_id}.restlets.api.netsuite.com"

    @staticmethod
    def _endpoint(api: Literal["suiteql", "rest"] = "rest"):
        if api == "suiteql":
            return "/query/v1"
        return "/record/v1"

    @classmethod
    def _format_url(cls, url: str, **kwargs) -> str:
        """
        Return the complete url to make the request
        """

        if url == "/suiteql":
            url = f"{cls._base_url()}{cls._endpoint("suiteql")}/{url.lstrip('/')}"
        elif url.startswith("/app/site/hosting/restlet.nl"):
            url = f"{cls._base_url('restlet')}/{url.lstrip('/')}"
        elif not url.startswith("http"):
            url = f"{cls._base_url()}{cls._endpoint()}/{url.lstrip('/')}"

        if kwargs:
            url += "?" + urlencode(kwargs)

        return url

    @classmethod
    async def get_request(cls, url: str, response_codes: tuple[int, ...] = (200, 404), **kwargs) -> httpx.Response:
        """
        Make a GET request
        Args:
            url: URL to append to the base url
            response_codes: Valid response codes to return from the server.
        Returns:
        """

        response = await cls.request("GET", url, response_codes=response_codes, **kwargs)

        if response.status_code == 404:
            raise DoesNotExistError(f"Object does not exist: {url}")

        return response

    @classmethod
    async def delete_request(cls, url: str, response_codes: tuple[int, ...] = (204,), **kwargs) -> httpx.Response:
        """
        Make a DELETE request
        Args:
            url: URL to append to the base url
            response_codes: Valid response codes to return from the server.
        Returns:
        """
        return await cls.request("DELETE", url, response_codes=response_codes, **kwargs)

    @classmethod
    async def query_request(cls, query: str, **kwargs) -> dict:
        """
        Make a query request
        Args:
            query: SuiteQL query to run
        Returns:
        """

        url = "/suiteql"
        data = {"q": query}
        headers = {"Prefer": "transient"}
        response = await cls.request("POST", url=url, data=data, response_codes=(200, 400), headers=headers, **kwargs)

        if response.status_code == 400:
            raise NetSuiteResponseError(f"SuiteQL query failed: {response.text} {query}")

        return response.json()
