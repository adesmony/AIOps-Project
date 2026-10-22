from typing import Annotated

from fastapi import Depends, Request

from app.contracts import PublicUser
from app.registry import Services, get_services


def services_dependency() -> Services:
    return get_services()


async def current_user(
    request: Request,
    services: Annotated[Services, Depends(services_dependency)],
) -> PublicUser:
    session_token = request.cookies.get(services.settings.session_cookie_name)
    return await services.auth.authenticate(session_token)


ServicesDependency = Annotated[Services, Depends(services_dependency)]
CurrentUser = Annotated[PublicUser, Depends(current_user)]
