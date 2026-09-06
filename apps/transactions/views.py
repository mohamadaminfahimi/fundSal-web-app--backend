from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Transaction
from .serializers import TransactionSerializer


class TransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        qs = Transaction.objects.filter(user=request.user).order_by("-created_at")
        serializer = TransactionSerializer(qs, many=True)
        return Response({"success": True, "data": serializer.data})


class TransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        txn = Transaction.objects.filter(user=request.user, id=kwargs.get("transaction_id")).first()
        if txn is None:
            return Response({"success": False, "error": {"code": "NOT_FOUND", "message": "تراکنش یافت نشد."}}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "data": TransactionSerializer(txn).data})
