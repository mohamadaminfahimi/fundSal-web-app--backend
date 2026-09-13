# apps/admin_api/views.py

from __future__ import annotations

import logging
from decimal import Decimal

from apps.common.signals import clear_user_caches
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.invoices.models import Invoice
from apps.market.services.price_service import price_service
from apps.trading.models import Order
from apps.users.views import CustomResponse
from apps.wallet.models import AssetHolding, Wallet
from apps.wallet.services import WalletService

from .permissions import IsAdminUser
from .serializers import (
    AdminAssetAdjustSerializer,
    AdminInvoiceSerializer,
    AdminInvoiceUpdateSerializer,
    AdminLoginSerializer,
    AdminOrderSerializer,
    AdminOrderUpdateSerializer,
    AdminPriceSerializer,
    AdminUserListSerializer,
    AdminWalletAdjustSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# ============================================================
# Helpers
# ============================================================

def normalize_phone(phone: str) -> str:
    """
    تبدیل شماره موبایل ایران به فرمت بین‌المللی:
      09121234567  → +989121234567
      9121234567   → +989121234567
      +989121234567 → +989121234567
    """
    if not phone:
        return phone
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("0"):
        digits = digits[1:]
    if not digits.startswith("98"):
        digits = "98" + digits
    return "+" + digits


def _extract_validation_errors(exc) -> dict[str, list[str]]:
    """
    از یک ValidationError جنگو، دیکشنری {field: [messages]} بیرون بکش.
    """
    errors: dict[str, list[str]] = {}
    message_dict = getattr(exc, "message_dict", None)
    if message_dict:
        for field, msgs in message_dict.items():
            errors[field] = [str(m) for m in msgs]
    else:
        messages = getattr(exc, "messages", None) or [str(exc)]
        errors["_error"] = [str(m) for m in messages]
    return errors


# ============================================================
# Auth
# ============================================================

class AdminLoginView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "اطلاعات ناقص",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "ایمیل یا رمز عبور اشتباه است"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {"success": False, "message": "ایمیل یا رمز عبور اشتباه است"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"success": False, "message": "حساب کاربری غیرفعال است"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.is_staff:
            return Response(
                {"success": False, "message": "شما دسترسی ادمین ندارید"},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response(
            {
                "success": True,
                "message": "ورود با موفقیت انجام شد.",
                "data": {
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "full_name": f"{user.first_name} {user.last_name}".strip()
                        or user.email,
                        "is_staff": user.is_staff,
                    },
                    "access_token": access_token,
                },
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            settings.ADMIN_REFRESH_COOKIE,
            refresh_token,
            max_age=7 * 24 * 3600,
            httponly=True,
            samesite="Lax",
            secure=not settings.DEBUG,
            path="/",
        )

        response.set_cookie(
            settings.ADMIN_ACCESS_COOKIE,
            access_token,
            max_age=15 * 60,
            httponly=False,
            samesite="Lax",
            secure=not settings.DEBUG,
            path="/",
        )

        return response


class AdminLogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        response = Response({"success": True, "message": "خروج انجام شد"})
        response.delete_cookie(settings.ADMIN_ACCESS_COOKIE, path="/")
        response.delete_cookie(settings.ADMIN_REFRESH_COOKIE, path="/")
        return response


class AdminProfileView(APIView):
    """GET /api/v1/admin/auth/profile/"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        user = request.user
        return CustomResponse.success(data={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": f"{user.first_name} {user.last_name}".strip(),
            "is_staff": user.is_staff,
        })


# ============================================================
# Dashboard
# ============================================================

class AdminDashboardStatsView(APIView):
    """GET /api/v1/admin/dashboard/stats/"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            cache_key = "admin:dashboard:stats"
            cached = cache.get(cache_key)
            if cached:
                return CustomResponse.success(data=cached)

            today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

            total_users = User.objects.filter(is_staff=False).count()
            active_users = User.objects.filter(is_staff=False, is_active=True).count()
            new_users_today = User.objects.filter(
                is_staff=False, date_joined__gte=today
            ).count()

            pending_invoices = Invoice.objects.filter(status="pending").count()
            paid_invoices = Invoice.objects.filter(status="paid").count()
            failed_invoices = Invoice.objects.filter(status="failed").count()

            total_deposit = Invoice.objects.filter(
                transaction_type="deposit", status="paid"
            ).aggregate(total=Sum("total_toman"))["total"] or Decimal("0")

            total_withdraw = Invoice.objects.filter(
                transaction_type="withdraw", status="paid"
            ).aggregate(total=Sum("total_toman"))["total"] or Decimal("0")

            pending_orders = Order.objects.filter(status="pending").count()
            filled_orders = Order.objects.filter(status="filled").count()

            data = {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "new_today": new_users_today,
                },
                "invoices": {
                    "pending": pending_invoices,
                    "paid": paid_invoices,
                    "failed": failed_invoices,
                    "total_deposit": str(total_deposit),
                    "total_withdraw": str(total_withdraw),
                },
                "orders": {
                    "pending": pending_orders,
                    "filled": filled_orders,
                },
            }

            cache.set(cache_key, data, 60)
            return CustomResponse.success(data=data)

        except Exception as e:
            logger.exception(f"❌ Admin dashboard error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


# ============================================================
# Invoices
# ============================================================

class AdminInvoiceListView(APIView):
    """GET /api/v1/admin/invoices/"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            queryset = Invoice.objects.select_related(
                "user", "reviewed_by"
            ).prefetch_related("items")

            status_filter = request.query_params.get("status")
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            type_filter = request.query_params.get("transaction_type")
            if type_filter:
                queryset = queryset.filter(transaction_type=type_filter)

            user_email = request.query_params.get("user_email")
            if user_email:
                queryset = queryset.filter(user__email__icontains=user_email)

            number = request.query_params.get("number")
            if number:
                queryset = queryset.filter(number__icontains=number)

            queryset = queryset.order_by("-created_at")

            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            invoices = queryset[start:end]

            return CustomResponse.success(data={
                "results": AdminInvoiceSerializer(invoices, many=True).data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            })

        except Exception as e:
            logger.exception(f"❌ AdminInvoiceListView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


class AdminInvoiceDetailView(APIView):
    """GET/PATCH /api/v1/admin/invoices/{id}/"""
    permission_classes = [IsAdminUser]

    def get(self, request, invoice_id):
        try:
            try:
                invoice = Invoice.objects.select_related(
                    "user", "reviewed_by"
                ).prefetch_related("items").get(id=invoice_id)
            except Invoice.DoesNotExist:
                return CustomResponse.error(
                    code="GEN_002",
                    detail="فاکتور یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            return CustomResponse.success(data=AdminInvoiceSerializer(invoice).data)
        except Exception as e:
            logger.exception(f"❌ AdminInvoiceDetailView GET error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)

    @transaction.atomic
    def patch(self, request, invoice_id):
        try:
            try:
                invoice = Invoice.objects.get(id=invoice_id)
            except Invoice.DoesNotExist:
                return CustomResponse.error(
                    code="GEN_002",
                    detail="فاکتور یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # ============================================================
            # گرفتن ورودی‌ها
            # ============================================================
            new_status = request.data.get("status")
            admin_note = request.data.get("admin_note", None)
            mode = request.data.get("mode", "normal")  # ✅ "normal" یا "manual"
            # mode="manual" یعنی ادمین می‌خواهد فقط وضعیت را دستی عوض کند
            # و هیچ تاثیری روی کیف پول نداشته باشد

            old_status = invoice.status

            # ============================================================
            # اگر توضیحات ارسال شده بود، ذخیره کن
            # ============================================================
            if admin_note is not None:
                invoice.admin_note = admin_note

            # ============================================================
            # اگر وضعیت تغییر نکرده
            # ============================================================
            if not new_status or new_status == old_status:
                invoice.save()
                return CustomResponse.success(
                    data=AdminInvoiceSerializer(invoice).data,
                    message="توضیحات به‌روزرسانی شد.",
                )

            # ============================================================
            # ✅ اگر mode="manual" → فقط وضعیت عوض شود، بدون دست زدن به کیف پول
            # ============================================================
            if mode == "manual":
                invoice.status = new_status
                invoice.reviewed_by = request.user
                invoice.reviewed_at = timezone.now()
                invoice.save()

                for key in (
                    f"invoices:user:{invoice.user.id}",
                    f"wallet:user:{invoice.user.id}",
                    f"dashboard:user:{invoice.user.id}",
                    "admin:dashboard:stats",
                ):
                    cache.delete(key)

                return CustomResponse.success(
                    data=AdminInvoiceSerializer(invoice).data,
                    message=f"وضعیت فاکتور به‌صورت دستی به «{new_status}» تغییر یافت (بدون اثر روی کیف پول).",
                )

            # ============================================================
            # حالت عادی: منطق تجاری
            # ============================================================

            # ✅ تایید فاکتور
            if new_status == "paid" and old_status != "paid":
                invoice.mark_as_paid(reviewed_by=request.user, admin_note=admin_note or "")

                # واریز (deposit) → اضافه کردن به کیف پول
                if invoice.transaction_type == "deposit":
                    WalletService.credit(
                        invoice.user,
                        invoice.total_toman,
                        reason=f"تایید فاکتور واریز {invoice.number}",
                    )

                # ✅ برداشت (withdraw) → فقط پول از کیف پول کاربر کم شود
                elif invoice.transaction_type == "withdraw":
                    try:
                        w = Wallet.objects.select_for_update().get(user=invoice.user)

                        # اگر پول در pending_balance است، از آن کم کن
                        # (چون هنگام درخواست برداشت، معمولاً از available به pending منتقل می‌شود)
                        if w.pending_balance >= invoice.total_toman:
                            w.pending_balance -= invoice.total_toman
                        else:
                            # اگر pending کافی نبود، از available کم کن
                            w.available_balance -= invoice.total_toman

                        w.save()
                    except Wallet.DoesNotExist:
                        pass

            # ✅ رد فاکتور
            elif new_status == "failed" and old_status != "failed":
                invoice.mark_as_failed(reviewed_by=request.user, admin_note=admin_note or "")

                # ✅ برداشت (withdraw) رد شد → پول را به کاربر برگردان
                if invoice.transaction_type == "withdraw":
                    try:
                        w = Wallet.objects.select_for_update().get(user=invoice.user)

                        # اگر در pending بود، از pending کم کن و به available برگردان
                        if w.pending_balance >= invoice.total_toman:
                            w.pending_balance -= invoice.total_toman
                            w.available_balance += invoice.total_toman
                        else:
                            # اگر در pending نبود، فقط به available اضافه کن
                            w.available_balance += invoice.total_toman
                        w.save()
                    except Wallet.DoesNotExist:
                        pass

            else:
                # سایر حالت‌ها
                invoice.status = new_status
                invoice.reviewed_by = request.user
                invoice.reviewed_at = timezone.now()
                invoice.save()

            # ✅ پاک کردن کش
            for key in (
                f"invoices:user:{invoice.user.id}",
                f"wallet:user:{invoice.user.id}",
                f"dashboard:user:{invoice.user.id}",
                "admin:dashboard:stats",
            ):
                cache.delete(key)

            return CustomResponse.success(
                data=AdminInvoiceSerializer(invoice).data,
                message="فاکتور با موفقیت به‌روزرسانی شد.",
            )

        except Exception as e:
            logger.exception(f"❌ AdminInvoiceDetailView PATCH error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


# ============================================================
# Orders
# ============================================================

class AdminOrderListView(APIView):
    """GET /api/v1/admin/orders/"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            queryset = Order.objects.select_related("user")

            status_filter = request.query_params.get("status")
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            side = request.query_params.get("side")
            if side:
                queryset = queryset.filter(side=side)

            metal_code = request.query_params.get("metal_code")
            if metal_code:
                queryset = queryset.filter(metal_code=metal_code)

            user_email = request.query_params.get("user_email")
            if user_email:
                queryset = queryset.filter(user__email__icontains=user_email)

            queryset = queryset.order_by("-created_at")

            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            orders = queryset[start:end]

            return CustomResponse.success(data={
                "results": AdminOrderSerializer(orders, many=True).data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            })

        except Exception as e:
            logger.exception(f"❌ AdminOrderListView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


class AdminOrderDetailView(APIView):
    """PATCH /api/v1/admin/orders/{id}/"""
    permission_classes = [IsAdminUser]

    def patch(self, request, order_id):
        try:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                return CustomResponse.error(
                    code="GEN_002",
                    detail="سفارش یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            new_status = request.data.get("status")
            admin_note = request.data.get("admin_note", "")

            if not new_status:
                return CustomResponse.error(
                    code="INP_001",
                    detail="وضعیت الزامی است.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            old_status = order.status

            if new_status == old_status:
                # فقط توضیحات را ذخیره کن
                order.metadata = {
                    **(order.metadata or {}),
                    "admin_note": admin_note,
                }
                order.save()
                return CustomResponse.success(
                    data=AdminOrderSerializer(order).data,
                    message="توضیحات ذخیره شد.",
                )

            # ============================================================
            # تکمیل سفارش فروش — پول به کاربر
            # ============================================================
            if new_status == "filled" and order.side == "sell" and old_status != "filled":
                try:
                    wallet = Wallet.objects.select_for_update().get(user=order.user)
                    wallet.pending_balance -= order.total_amount
                    wallet.available_balance += order.total_amount
                    wallet.save()
                except Wallet.DoesNotExist:
                    pass

            # ============================================================
            # تکمیل سفارش خرید — دارایی به کاربر
            # ============================================================
            if new_status == "filled" and order.side == "buy" and old_status != "filled":
                try:
                    holding, _ = AssetHolding.objects.get_or_create(
                        user=order.user, metal_code=order.metal_code,
                        defaults={"available_quantity": Decimal("0")},
                    )
                    holding.available_quantity += order.quantity
                    holding.save()
                except Exception:
                    pass

            # ============================================================
            # لغو/رد سفارش خرید — برگرداندن پول به کاربر
            # ============================================================
            if new_status in ("cancelled", "rejected") and order.side == "buy" and old_status not in ("cancelled", "rejected"):
                try:
                    wallet = Wallet.objects.select_for_update().get(user=order.user)
                    wallet.available_balance += order.total_amount
                    wallet.save()
                except Wallet.DoesNotExist:
                    pass

            # ============================================================
            # لغو/رد سفارش فروش — برگرداندن دارایی به کاربر
            # ============================================================
            if new_status in ("cancelled", "rejected") and order.side == "sell" and old_status not in ("cancelled", "rejected"):
                try:
                    holding, _ = AssetHolding.objects.get_or_create(
                        user=order.user, metal_code=order.metal_code,
                        defaults={"available_quantity": Decimal("0")},
                    )
                    holding.available_quantity += order.quantity
                    holding.save()

                    wallet = Wallet.objects.select_for_update().get(user=order.user)
                    wallet.pending_balance -= order.total_amount
                    wallet.save()
                except Exception:
                    pass

            # ============================================================
            # ذخیره وضعیت + توضیحات
            # ============================================================
            order.status = new_status
            order.metadata = {
                **(order.metadata or {}),
                "admin_note": admin_note,
                "reviewed_at": timezone.now().isoformat(),
                "reviewed_by": request.user.email,
            }
            order.save()

            # ✅ پاک کردن کش
            clear_user_caches(order.user.id)
            cache.delete("admin:dashboard:stats")

            return CustomResponse.success(
                data=AdminOrderSerializer(order).data,
                message="سفارش با موفقیت به‌روزرسانی شد.",
            )

        except Exception as e:
            logger.exception(f"❌ AdminOrderDetailView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


# ============================================================
# Users
# ============================================================

class AdminUserListView(APIView):
    """GET /api/v1/admin/users/"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            include_staff = request.query_params.get(
                "include_staff", "false"
            ).lower() in ("true", "1", "yes")

            if include_staff:
                queryset = User.objects.filter(
                    Q(is_staff=False) | Q(id=request.user.id)
                ).select_related("wallet")
            else:
                queryset = User.objects.filter(
                    is_staff=False
                ).select_related("wallet")

            search = request.query_params.get("search")
            if search:
                queryset = queryset.filter(
                    Q(email__icontains=search)
                    | Q(first_name__icontains=search)
                    | Q(last_name__icontains=search)
                    | Q(phone_number__icontains=search)
                )

            is_active = request.query_params.get("is_active")
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == "true")

            queryset = queryset.order_by("-date_joined")

            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            users = queryset[start:end]

            return CustomResponse.success(data={
                "results": AdminUserListSerializer(users, many=True).data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            })

        except Exception as e:
            logger.exception(f"❌ AdminUserListView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


class AdminUserDetailView(APIView):
    """GET /api/v1/admin/users/{id}/"""
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        try:
            try:
                user = User.objects.select_related("wallet").get(id=user_id)
            except User.DoesNotExist:
                return CustomResponse.error(
                    code="GEN_002",
                    detail="کاربر یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CustomResponse.success(
                data=AdminUserListSerializer(user).data
            )
        except Exception as e:
            logger.exception(f"❌ AdminUserDetailView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


class AdminUserCreateView(APIView):
    """POST /api/v1/admin/users/create/"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            email = (request.data.get("email") or "").strip().lower()
            password = request.data.get("password") or ""
            first_name = (request.data.get("first_name") or "").strip()
            last_name = (request.data.get("last_name") or "").strip()
            raw_phone = (request.data.get("phone_number") or "").strip() or None
            is_active = bool(request.data.get("is_active", True))
            is_staff = bool(request.data.get("is_staff", False))

            errors: dict[str, list[str]] = {}

            # ایمیل
            if not email:
                errors.setdefault("email", []).append("ایمیل الزامی است.")
            elif "@" not in email:
                errors.setdefault("email", []).append("فرمت ایمیل صحیح نیست.")
            elif User.objects.filter(email__iexact=email).exists():
                errors.setdefault("email", []).append("این ایمیل قبلاً ثبت شده است.")

            # رمز
            if not password:
                errors.setdefault("password", []).append("رمز عبور الزامی است.")
            elif len(password) < 6:
                errors.setdefault("password", []).append(
                    "رمز عبور باید حداقل ۶ کاراکتر باشد."
                )

            # نام
            if not first_name:
                errors.setdefault("first_name", []).append("نام الزامی است.")
            if not last_name:
                errors.setdefault("last_name", []).append("نام خانوادگی الزامی است.")

            # موبایل
            normalized_phone = None
            if not raw_phone:
                errors.setdefault("phone_number", []).append("شماره موبایل الزامی است.")
            else:
                digits = "".join(c for c in raw_phone if c.isdigit())
                if not digits.startswith("09") or len(digits) != 11:
                    errors.setdefault("phone_number", []).append(
                        "شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد."
                    )
                else:
                    normalized_phone = normalize_phone(raw_phone)
                    if User.objects.filter(
                        Q(phone_number=raw_phone) | Q(phone_number=normalized_phone)
                    ).exists():
                        errors.setdefault("phone_number", []).append(
                            "این شماره موبایل قبلاً ثبت شده است."
                        )

            if errors:
                return Response(
                    {
                        "success": False,
                        "message": "لطفاً خطاهای زیر را برطرف کنید.",
                        "errors": errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ✅ ساخت کاربر
            try:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=normalized_phone,
                    is_active=is_active,
                    is_staff=is_staff,
                )
            except Exception as e:
                import traceback
                print("🔥 create_user ERROR:", traceback.format_exc())

                # اگر ValidationError جنگو بود
                from django.core.exceptions import ValidationError as DjangoValidationError
                if isinstance(e, DjangoValidationError):
                    errs = _extract_validation_errors(e)
                    return Response(
                        {
                            "success": False,
                            "message": "لطفاً خطاهای زیر را برطرف کنید.",
                            "errors": errs,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                return Response(
                    {
                        "success": False,
                        "message": f"خطا در ساخت کاربر: {type(e).__name__}",
                        "errors": {"_error": [str(e)]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ✅ کیف پول
            try:
                Wallet.objects.get_or_create(user=user)
            except Exception:
                import traceback
                print("🔥 Wallet ERROR:", traceback.format_exc())

            return CustomResponse.success(
                data=AdminUserListSerializer(user).data,
                message="کاربر با موفقیت ساخته شد.",
            )

        except Exception as e:
            import traceback
            print("🔥 AdminUserCreateView UNEXPECTED ERROR:", traceback.format_exc())
            logger.exception(f"❌ AdminUserCreateView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


class AdminUserUpdateView(APIView):
    """PATCH /api/v1/admin/users/{id}/update/"""
    permission_classes = [IsAdminUser]

    def patch(self, request, user_id):
        try:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return CustomResponse.error(
                    code="GEN_002", detail="کاربر یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            data = request.data
            errors: dict[str, list[str]] = {}

            # ایمیل
            if "email" in data:
                new_email = (data["email"] or "").strip().lower()
                if not new_email:
                    errors.setdefault("email", []).append("ایمیل نمی‌تواند خالی باشد.")
                elif "@" not in new_email:
                    errors.setdefault("email", []).append("فرمت ایمیل صحیح نیست.")
                elif (
                    new_email != user.email
                    and User.objects.filter(email__iexact=new_email)
                    .exclude(id=user.id).exists()
                ):
                    errors.setdefault("email", []).append("این ایمیل قبلاً ثبت شده است.")

            # موبایل
            new_phone_raw = None
            normalized_phone = None
            if "phone_number" in data:
                new_phone_raw = (data["phone_number"] or "").strip() or None
                if new_phone_raw:
                    digits = "".join(c for c in new_phone_raw if c.isdigit())
                    if not digits.startswith("09") or len(digits) != 11:
                        errors.setdefault("phone_number", []).append(
                            "شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد."
                        )
                    else:
                        normalized_phone = normalize_phone(new_phone_raw)
                        if User.objects.filter(
                            Q(phone_number=new_phone_raw)
                            | Q(phone_number=normalized_phone)
                        ).exclude(id=user.id).exists():
                            errors.setdefault("phone_number", []).append(
                                "این شماره موبایل قبلاً ثبت شده است."
                            )

            # رمز
            if data.get("password") and len(data["password"]) < 6:
                errors.setdefault("password", []).append(
                    "رمز عبور باید حداقل ۶ کاراکتر باشد."
                )

            if errors:
                return Response(
                    {
                        "success": False,
                        "message": "لطفاً خطاهای زیر را برطرف کنید.",
                        "errors": errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ✅ اعمال تغییرات
            if "email" in data:
                user.email = (data["email"] or "").strip().lower()
            if "first_name" in data:
                user.first_name = (data["first_name"] or "").strip()
            if "last_name" in data:
                user.last_name = (data["last_name"] or "").strip()
            if "phone_number" in data:
                user.phone_number = normalized_phone
            if "is_active" in data:
                user.is_active = bool(data["is_active"])
            if "is_staff" in data:
                user.is_staff = bool(data["is_staff"])
            if data.get("password"):
                user.set_password(data["password"])

            try:
                user.full_clean(exclude=["password"])
                user.save()
            except Exception as e:
                import traceback
                print("🔥 user.save ERROR:", traceback.format_exc())

                from django.core.exceptions import ValidationError as DjangoValidationError
                if isinstance(e, DjangoValidationError):
                    errs = _extract_validation_errors(e)
                    return Response(
                        {
                            "success": False,
                            "message": "لطفاً خطاهای زیر را برطرف کنید.",
                            "errors": errs,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                return Response(
                    {
                        "success": False,
                        "message": f"خطا در ذخیره: {type(e).__name__}",
                        "errors": {"_error": [str(e)]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cache.delete(f"dashboard:user:{user.id}")

            return CustomResponse.success(
                data=AdminUserListSerializer(user).data,
                message="اطلاعات کاربر به‌روزرسانی شد.",
            )

        except Exception as e:
            import traceback
            print("🔥 AdminUserUpdateView UNEXPECTED ERROR:", traceback.format_exc())
            logger.exception(f"❌ AdminUserUpdateView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


class AdminUserTransactionsView(APIView):
    """GET /api/v1/admin/users/{id}/transactions/"""
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        try:
            from apps.transactions.models import Transaction
            qs = Transaction.objects.filter(user_id=user_id).order_by("-created_at")[:50]
            data = [
                {
                    "id": t.id,
                    "type": getattr(t, "transaction_type", None)
                    or getattr(t, "type", None),
                    "amount": str(getattr(t, "amount", "0")),
                    "description": getattr(t, "description", ""),
                    "created_at": t.created_at.isoformat()
                    if hasattr(t, "created_at")
                    else None,
                }
                for t in qs
            ]
            return CustomResponse.success(data=data)
        except Exception as e:
            logger.exception(f"❌ AdminUserTransactionsView error: {e}")
            return CustomResponse.success(data=[])


class AdminWalletAdjustView(APIView):
    """POST /api/v1/admin/users/{id}/wallet/adjust/"""
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        try:
            from apps.transactions.models import Transaction

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return CustomResponse.error(
                    code="GEN_002",
                    detail="کاربر یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            serializer = AdminWalletAdjustSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomResponse.validation_errors(serializer.errors)

            action = serializer.validated_data["action"]
            amount = serializer.validated_data["amount"]
            description = (
                serializer.validated_data.get("description")
                or serializer.validated_data.get("reason")
                or ("شارژ توسط ادمین" if action == "credit" else "برداشت توسط ادمین")
            )

            if action == "credit":
                wallet = WalletService.credit(user, amount, reason=description)
                txn_type = "deposit"
            else:
                wallet = WalletService.debit(user, amount, reason=description)
                txn_type = "withdrawal"

            # ✅ ثبت تراکنش با توضیحات
            txn = Transaction.objects.create(
                user=user,
                transaction_type=txn_type,
                amount=amount,
                currency="IRR",
                status="completed",
                reference_id=f"admin-adjust-{request.user.id}-{user.id}",
                metadata={
                    "description": description,
                    "by_admin": request.user.email,
                    "action": action,
                    "source": "admin_panel",
                },
            )

            # ✅ پاک کردن کش
            for key in (
                f"wallet:user:{user.id}",
                f"assets:user:{user.id}",
                f"portfolio:user:{user.id}",
                f"dashboard:user:{user.id}",
                f"transactions:user:{user.id}",
                "admin:dashboard:stats",
            ):
                cache.delete(key)


            return CustomResponse.success(
                data={
                    "balance": str(wallet.available_balance),
                    "transaction_id": txn.id,
                },
                message=f"کیف پول با موفقیت {'شارژ' if action == 'credit' else 'برداشت'} شد.",
            )

        except Exception as e:
            logger.exception(f"❌ AdminWalletAdjustView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)
        

class AdminAssetAdjustView(APIView):
    """POST /api/v1/admin/users/{id}/assets/adjust/"""
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        try:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return CustomResponse.error(
                    code="GEN_002",
                    detail="کاربر یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            serializer = AdminAssetAdjustSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomResponse.validation_errors(serializer.errors)

            action = serializer.validated_data["action"]
            metal_code = serializer.validated_data["metal_code"]
            quantity = serializer.validated_data["quantity"]

            holding, _ = AssetHolding.objects.get_or_create(
                user=user, metal_code=metal_code,
                defaults={"available_quantity": Decimal("0")},
            )

            if action == "credit":
                holding.available_quantity += quantity
            else:
                if holding.available_quantity < quantity:
                    return CustomResponse.error(
                        code="INP_002",
                        detail=f"موجودی {metal_code} کافی نیست.",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                holding.available_quantity -= quantity

            holding.save()

            for key in (
                f"assets:user:{user.id}",
                f"dashboard:user:{user.id}",
                "admin:dashboard:stats",
            ):
                cache.delete(key)

            return CustomResponse.success(
                data={"quantity": str(holding.available_quantity)},
                message=f"{metal_code} با موفقیت {'اضافه' if action == 'credit' else 'کم'} شد.",
            )

        except Exception as e:
            logger.exception(f"❌ AdminAssetAdjustView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


# ============================================================
# Prices
# ============================================================

class AdminPricesView(APIView):
    """GET/PATCH /api/v1/admin/prices/"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            prices = price_service.get_prices()

            manual_prices = cache.get("admin:manual_prices") or {}
            confidence_range = cache.get("admin:confidence_range", Decimal("0.5"))

            return CustomResponse.success(data={
                "prices": [
                    {
                        "metal_code": p["metal_code"],
                        "price": str(p["price"]),
                        "change_percent": str(p["change_percent"]),
                        "updated_at": p["updated_at"],
                    }
                    for p in prices
                ],
                "manual_prices": {
                    k: str(v) for k, v in manual_prices.items()
                },
                "confidence_range_percent": str(confidence_range),
                "gold_buy_price": manual_prices.get("GOLD_BUY", ""),
                "gold_sell_price": manual_prices.get("GOLD_SELL", ""),
                "silver_buy_price": manual_prices.get("SILVER_BUY", ""),
                "silver_sell_price": manual_prices.get("SILVER_SELL", ""),
            })

        except Exception as e:
            logger.exception(f"❌ AdminPricesView GET error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)

    def patch(self, request):
        try:
            serializer = AdminPriceSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomResponse.validation_errors(serializer.errors)

            data = serializer.validated_data

            manual_prices = cache.get("admin:manual_prices") or {}

            if "gold_buy_price" in data:
                manual_prices["GOLD_BUY"] = str(data["gold_buy_price"])
            if "gold_sell_price" in data:
                manual_prices["GOLD_SELL"] = str(data["gold_sell_price"])
            if "silver_buy_price" in data:
                manual_prices["SILVER_BUY"] = str(data["silver_buy_price"])
            if "silver_sell_price" in data:
                manual_prices["SILVER_SELL"] = str(data["silver_sell_price"])

            cache.set("admin:manual_prices", manual_prices)

            if "confidence_range_percent" in data:
                cache.set(
                    "admin:confidence_range",
                    data["confidence_range_percent"],
                )

            cache.delete("market:prices")

            logger.info(f"✅ Prices updated by {request.user.email}")

            return CustomResponse.success(message="قیمت‌ها با موفقیت به‌روزرسانی شد.")

        except Exception as e:
            logger.exception(f"❌ AdminPricesView PATCH error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)




class AdminTransactionDeleteView(APIView):
    """DELETE /api/v1/admin/transactions/{id}/"""
    permission_classes = [IsAdminUser]

    def delete(self, request, transaction_id):
        try:
            from apps.transactions.models import Transaction

            try:
                txn = Transaction.objects.get(id=transaction_id)
            except Transaction.DoesNotExist:
                return CustomResponse.error(
                    code="GEN_002",
                    detail="تراکنش یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # ✅ برگرداندن اثر تراکنش روی کیف پول
            from apps.wallet.models import Wallet
            try:
                wallet = Wallet.objects.get(user=txn.user)
                meta = txn.metadata or {}
                action = meta.get("action")

                if txn.transaction_type == "deposit":
                    # شارژ توسط ادمین → کم کن
                    wallet.available_balance -= txn.amount
                    wallet.save()
                elif txn.transaction_type == "withdrawal":
                    # برداشت توسط ادمین → برگردان
                    wallet.available_balance += txn.amount
                    wallet.save()
                elif txn.transaction_type == "adjustment":
                    # تنظیم فلز → برگردان
                    metal = meta.get("metal_code")
                    qty = Decimal(meta.get("quantity", "0"))
                    if metal and action:
                        holding, _ = AssetHolding.objects.get_or_create(
                            user=txn.user, metal_code=metal,
                            defaults={"available_quantity": Decimal("0")},
                        )
                        if action == "credit":
                            holding.available_quantity -= qty
                        else:
                            holding.available_quantity += qty
                        holding.save()
            except Wallet.DoesNotExist:
                pass

            user_id = txn.user_id
            txn.delete()

            # ✅ پاک کردن کش
            for key in (
                f"wallet:user:{user_id}",
                f"assets:user:{user_id}",
                f"dashboard:user:{user_id}",
                f"transactions:user:{user_id}",
                "admin:dashboard:stats",
            ):
                cache.delete(key)

            return CustomResponse.success(
                message="تراکنش با موفقیت حذف و اثر آن برگردانده شد.",
            )

        except Exception as e:
            logger.exception(f"❌ AdminTransactionDeleteView error: {e}")
            return CustomResponse.error(code="GEN_001", status_code=500)


                
            