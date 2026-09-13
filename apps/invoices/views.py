# apps/invoices/views.py

from __future__ import annotations

import logging

from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.views import CustomResponse
from .models import Invoice
from .serializers import CreateInvoiceSerializer, InvoiceSerializer

logger = logging.getLogger(__name__)


class InvoiceListView(APIView):
    """GET /api/v1/invoices/ - لیست فاکتورهای کاربر"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            cache_key = f"invoices:user:{user.id}"
            
            # ✅ از کش
            cached = cache.get(cache_key)
            if cached is not None:
                return CustomResponse.success(data=cached)
            
            # ✅ از DB
            invoices = Invoice.objects.filter(user=user).prefetch_related("items")
            data = InvoiceSerializer(invoices, many=True).data
            
            cache.set(cache_key, data, 60)  # ۱ دقیقه
            
            return CustomResponse.success(data=data)
        
        except Exception as e:
            logger.exception(f"❌ Error in InvoiceListView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreateInvoiceView(APIView):
    """
    POST /api/v1/invoices/create/
    
    ساخت درخواست واریز یا برداشت
    
    Request:
    {
        "transaction_type": "deposit" | "withdraw",
        "amount": "1000000",
        "description": "توضیحات (اختیاری)",
        // برای برداشت:
        "shaba_number": "IR...",
        "account_name": "علی رضایی",
        "bank_name": "بانک ملت"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = CreateInvoiceSerializer(
                data=request.data,
                context={"request": request},
            )
            
            if not serializer.is_valid():
                return CustomResponse.validation_errors(serializer.errors)
            
            invoice = serializer.save()
            
            # ✅ پاک کردن کش فاکتورها
            cache.delete(f"invoices:user:{request.user.id}")
            
            logger.info(
                f"✅ Invoice created: {invoice.number} "
                f"({invoice.transaction_type}) by {request.user.email}"
            )
            
            return CustomResponse.success(
                data=InvoiceSerializer(invoice).data,
                message=f"درخواست {invoice.get_transaction_type_display()} با موفقیت ثبت شد.",
                status_code=status.HTTP_201_CREATED,
            )
        
        except Exception as e:
            logger.exception(f"❌ Error in CreateInvoiceView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InvoiceDetailView(APIView):
    """GET /api/v1/invoices/{id}/ - جزئیات فاکتور"""
    permission_classes = [IsAuthenticated]

    def get(self, request, invoice_id):
        try:
            try:
                invoice = Invoice.objects.prefetch_related("items").get(
                    id=invoice_id,
                    user=request.user,
                )
            except Invoice.DoesNotExist:
                return CustomResponse.error(
                    code="GEN_002",
                    detail="فاکتور یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            
            return CustomResponse.success(
                data=InvoiceSerializer(invoice).data,
            )
        
        except Exception as e:
            logger.exception(f"❌ Error in InvoiceDetailView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )