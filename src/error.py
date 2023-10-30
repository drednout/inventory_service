import enum
import logging

from aiohttp import web

from aiohttp.web_exceptions import (
    HTTPBadRequest, HTTPClientError
)
from aiohttp_swagger3.swagger_route import RequestValidationFailed


@enum.unique
class ApiErrorCode(enum.Enum):
    validation_error = 'validation_error'
    schema_validation_error = 'schema_validation_error'
    db_error = 'db_error'
    server_error = 'server_error'
    logical_error = 'logical_error'


class ApiBaseError(Exception):
    def __init__(self, error_code: ApiErrorCode, error_message: str, context: dict, http_status_code: int):
        self.status = 'error'
        self.error_code = error_code
        self.error_message = error_message
        if context is None:
            context = {}
        self.context = context
        self.http_status_code = http_status_code

    def as_dict(self) -> dict:
        data = {
            'status': self.status,
            'error_code': str(self.error_code.name),
            'error_message': self.error_message,
            'context': self.context
        }
        return data


@web.middleware
async def error_middleware(request: web.Request, handler) -> web.StreamResponse:
    try:
        return await handler(request)
    except RequestValidationFailed as e:
        err = ApiValidationError(
            error_message="Invalid params in body",
            error_code=ApiErrorCode.schema_validation_error,
            context=e.errors
        )
        return web.json_response(status=err.http_status_code, data=err.as_dict())
    except ApiBaseError as err:
        return web.json_response(status=err.http_status_code, data=err.as_dict())
    except HTTPBadRequest as e:
        err = ApiValidationError(
            error_message=str(e),
            context={'reason': e.reason}
        )
        return web.json_response(status=err.http_status_code, data=err.as_dict())
    except HTTPClientError:
        raise

    except Exception as e:
        logging.exception(f"Internal server error. Error: {e}")
        err = ApiInternalError(
            error_message='Internal server error',
            context={'Exception': str(e)}
        )
        return web.json_response(status=err.http_status_code, data=err.as_dict())


class ApiValidationError(ApiBaseError):
    def __init__(self, error_message: str, error_code: ApiErrorCode = ApiErrorCode.validation_error, context: dict=None):
        super(ApiValidationError, self).__init__(error_code, error_message, context, 400)


class ApiInternalError(ApiBaseError):
    def __init__(self, error_message: str, error_code: ApiErrorCode = ApiErrorCode.server_error, context: dict=None):
        super(ApiInternalError, self).__init__(error_code, error_message, context, 500)


class ApiLogicalError(ApiBaseError):
    def __init__(self, error_message: str, error_code: ApiErrorCode = ApiErrorCode.logical_error, context: dict=None):
        super(ApiLogicalError, self).__init__(error_code, error_message, context, 420)
