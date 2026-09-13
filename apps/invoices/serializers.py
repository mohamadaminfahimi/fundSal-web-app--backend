# apps/invoices/serializers.py

from __future__ import annotations

from rest_framework import serializers

from .models import Invoice, InvoiceItem


# ============================================================
# Item Serializer
# ============================================================

class InvoiceItemSerializer(serializers.ModelSerializer):
    """سریالایزر آیتم‌های فاکتور"""
    
    class Meta:
        model = InvoiceItem
        fields = ["description", "amount"]


# ============================================================
# Display Serializer
# ============================================================

class InvoiceSerializer(serializers.ModelSerializer):
    """
    سریالایزر نمایش فاکتور
    
    ⚠️ فیلد date یک alias برای created_at هست
    (توی مدل فقط created_at وجود داره، ولی فرانت date می‌خواد)
    """
    
    items = InvoiceItemSerializer(many=True, read_only=True)
    
    # ✅ فیلد محاسباتی - created_at رو به date مپ می‌کنه
    date = serializers.DateTimeField(source="created_at", read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "transaction_type",
            "total_toman",
            "status",
            "date",          # ← فیلد محاسباتی (از created_at)
            "created_at",    # ← فیلد اصلی مدل
            "updated_at",
            "items",
            "metadata",
            "admin_note",
        ]
        read_only_fields = [
            "id",
            "number",
            "status",
            "date",
            "created_at",
            "updated_at",
        ]


# ============================================================
# Create Serializer
# ============================================================

class CreateInvoiceSerializer(serializers.Serializer):
    """
    سریالایزر ساخت فاکتور جدید (واریز یا برداشت)
    
    برای deposit:
        - transaction_type: "deposit"
        - amount: مبلغ (حداقل ۱۰,۰۰۰)
        - description: توضیحات (اختیاری)
    
    برای withdraw:
        - transaction_type: "withdraw"
        - amount: مبلغ (حداقل ۱۰,۰۰۰)
        - description: توضیحات (اختیاری)
        - shaba_number: شماره شبا (اجباری)
        - account_name: نام صاحب حساب (اجباری)
        - bank_name: نام بانک (اجباری)
    """
    
    transaction_type = serializers.ChoiceField(
        choices=["deposit", "withdraw"],
        required=True,
        error_messages={
            "invalid_choice": "نوع تراکنش باید deposit یا withdraw باشد.",
            "required": "نوع تراکنش الزامی است.",
        },
    )
    
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        required=True,
        min_value=10000,
        error_messages={
            "min_value": "حداقل مبلغ ۱۰,۰۰۰ تومان است.",
            "required": "مبلغ الزامی است.",
            "invalid": "مبلغ وارد شده معتبر نیست.",
        },
    )
    
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )
    
    # ✅ اطلاعات بانکی (فقط برای برداشت)
    shaba_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=26,
    )
    
    account_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
    )
    
    bank_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    
    # ========================================================
    # Validation
    # ========================================================
    
    def validate(self, attrs):
        transaction_type = attrs.get("transaction_type")
        amount = attrs.get("amount")
        
        # ✅ برای برداشت، اطلاعات بانکی اجباریه
        if transaction_type == "withdraw":
            errors = {}
            
            if not attrs.get("shaba_number", "").strip():
                errors["shaba_number"] = "شماره شبا الزامی است."
            elif len(attrs.get("shaba_number", "").strip()) < 24:
                errors["shaba_number"] = "شماره شبا باید حداقل ۲۴ کاراکتر باشد."
            
            if not attrs.get("account_name", "").strip():
                errors["account_name"] = "نام صاحب حساب الزامی است."
            
            if not attrs.get("bank_name", "").strip():
                errors["bank_name"] = "نام بانک الزامی است."
            
            if errors:
                raise serializers.ValidationError(errors)
            
            # ✅ چک کردن موجودی کافی برای برداشت
            request = self.context.get("request")
            if request and request.user:
                try:
                    wallet = request.user.wallet
                    if wallet.available_balance < amount:
                        raise serializers.ValidationError({
                            "amount": f"موجودی کیف پول کافی نیست. موجودی شما: {wallet.available_balance:,.0f} تومان"
                        })
                except Invoice.DoesNotExist:
                    pass
        
        return attrs
    
    # ========================================================
    # Create
    # ========================================================
    
    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        
        transaction_type = validated_data["transaction_type"]
        amount = validated_data["amount"]
        description = validated_data.get("description", "").strip()
        
        # ✅ اطلاعات اضافی برای metadata
        metadata = {}
        if transaction_type == "withdraw":
            metadata = {
                "shaba_number": validated_data.get("shaba_number", "").strip(),
                "account_name": validated_data.get("account_name", "").strip(),
                "bank_name": validated_data.get("bank_name", "").strip(),
            }
        
        # ✅ پیام پیش‌فرض اگه خالی بود
        type_label = "واریز" if transaction_type == "deposit" else "برداشت"
        if not description:
            description = f"درخواست {type_label} وجه"
        
        # ✅ ساخت فاکتور
        invoice = Invoice.objects.create(
            user=user,
            transaction_type=transaction_type,
            total_toman=amount,
            status=Invoice.Status.PENDING,
            metadata=metadata,
        )
        
        # ✅ اضافه کردن آیتم
        InvoiceItem.objects.create(
            invoice=invoice,
            description=description,
            amount=amount,
        )
        
        return invoice