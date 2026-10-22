from fastapi import APIRouter, Response, status

from app.contracts import AuthRequest, PublicUser, RegisterRequest
from app.dependencies import CurrentUser, ServicesDependency

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, services: ServicesDependency) -> PublicUser:
    return await services.auth.register(request)


@router.post("/login", response_model=PublicUser)
async def login(
    request: AuthRequest,
    response: Response,
    services: ServicesDependency,
) -> PublicUser:
    user, token = await services.auth.login(str(request.email), request.password)
    response.set_cookie(
        key=services.settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=not services.settings.is_development,
        samesite="strict" if not services.settings.is_development else "lax",
        max_age=services.settings.jwt_expiry_minutes * 60,
        path="/",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, services: ServicesDependency) -> None:
    response.delete_cookie(
        services.settings.session_cookie_name,
        path="/",
        secure=not services.settings.is_development,
        samesite="strict" if not services.settings.is_development else "lax",
    )


@router.get("/me", response_model=PublicUser)
async def me(user: CurrentUser) -> PublicUser:
    return user
