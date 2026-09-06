from __future__ import annotations

from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import clear_auth_cookies, set_auth_cookies
from .serializers import LoginSerializer, ProfileUpdateSerializer, RegisterSerializer, UserSerializer


class RegisterView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"success": True, "data": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response(
            {
                "success": True,
                "data": {
                    "user": UserSerializer(user).data,
                    "access_expires_at": timezone.now() + settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
                },
            },
            status=status.HTTP_200_OK,
        )
        set_auth_cookies(response, access_token, refresh_token)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logout(request)
        response = Response({"success": True, "data": {"message": "خروج با موفقیت انجام شد."}}, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        return response


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"success": False, "error": {"code": "REFRESH_TOKEN_MISSING", "message": "Refresh token یافت نشد."}}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token)
        except Exception:
            return Response({"success": False, "error": {"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token نامعتبر است."}}, status=status.HTTP_401_UNAUTHORIZED)

        access_token = str(refresh.access_token)
        response = Response({"success": True, "data": {"access_token": access_token}}, status=status.HTTP_200_OK)
        set_auth_cookies(response, access_token, str(refresh))
        return response


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({"success": True, "data": UserSerializer(request.user).data})

    def patch(self, request, *args, **kwargs):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": UserSerializer(request.user).data})
