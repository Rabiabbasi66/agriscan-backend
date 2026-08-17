from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from bson import ObjectId
from app.config import settings
from app.dependencies import get_db, get_current_active_user
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)

from app.schemas.user import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    UserOut,
    UserUpdate,
    ChangePassword,
)
from app.schemas.common import DataResponse

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/register",
    response_model=DataResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserRegister,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    existing = await db.users.find_one({"email": data.email})

    if existing:
        raise HTTPException(400, "Email already registered")

    user = {
        "email": data.email,
        "hashed_password": hash_password(data.password),
        "full_name": data.full_name,
        "phone": data.phone,
        "role": data.role,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    result = await db.users.insert_one(user)
    user["_id"] = result.inserted_id

    return DataResponse(
        message="Registration successful",
        data=UserOut(
            id=str(user["_id"]),
            email=user["email"],
            full_name=user["full_name"],
            phone=user.get("phone"),
            role=user["role"],
            is_active=True,
            profile_pic=user.get("profile_pic"),
            created_at=user["created_at"],
        ),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    data: UserLogin,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user = await db.users.find_one({"email": data.email})

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid credentials")

    access_token = create_access_token(
        subject=str(user["_id"]),
        extra={
            "email": user["email"],
            "role": user["role"],
        },
    )

    refresh_token = create_refresh_token(
        subject=str(user["_id"])
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=DataResponse[UserOut],
)
async def get_me(
    current_user=Depends(get_current_active_user),
):
    return DataResponse(
        data=UserOut(
            id=str(current_user["_id"]),
            email=current_user["email"],
            full_name=current_user["full_name"],
            phone=current_user.get("phone"),
            role=current_user["role"],
            is_active=current_user.get("is_active", True),
            profile_pic=current_user.get("profile_pic"),
            created_at=current_user["created_at"],
        )
    )


@router.post(
    "/refresh-token",
    response_model=TokenResponse,
)
async def refresh(
    body: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    payload = decode_refresh_token(body.refresh_token)

    if payload is None:
        raise HTTPException(401, "Invalid refresh token")

    user_id = payload["sub"]

    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(401, "User not found")

    access_token = create_access_token(
        subject=user_id,
        extra={
            "email": user["email"],
            "role": user["role"],
        },
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=body.refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.patch(
    "/me",
    response_model=DataResponse[UserOut],
)
async def update_me(
    body: UserUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    update = {
        k: v
        for k, v in body.model_dump().items()
        if v is not None
    }

    update["updated_at"] = datetime.now(timezone.utc)

    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": update},
    )

    user = await db.users.find_one({"_id": current_user["_id"]})

    return DataResponse(
        data=UserOut(
            id=str(user["_id"]),
            email=user["email"],
            full_name=user["full_name"],
            phone=user.get("phone"),
            role=user["role"],
            is_active=user.get("is_active", True),
            profile_pic=user.get("profile_pic"),
            created_at=user["created_at"],
        )
    )


@router.post(
    "/change-password",
    response_model=dict,
)
async def change_password(
    body: ChangePassword,
    current_user=Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not verify_password(body.old_password, current_user["hashed_password"]):
        raise HTTPException(400, "Old password is incorrect")

    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {
            "hashed_password": hash_password(body.new_password),
            "updated_at": datetime.now(timezone.utc),
        }},
    )

    return {
        "success": True,
        "message": "Password changed successfully",
    }