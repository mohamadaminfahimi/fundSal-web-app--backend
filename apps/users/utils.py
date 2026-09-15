def normalize_phone_number(phone: str) -> str:
    """
    تبدیل شماره موبایل به فرمت استاندارد E.164 (+98...)
    مثال‌های قابل قبول:
        09036610574
        9036610574
        +989036610574
        989036610574
    خروجی همیشه: +989036610574
    """
    if not phone:
        return phone

    phone = phone.strip().replace(" ", "").replace("-", "")

    if phone.startswith("+98"):
        return phone
    if phone.startswith("98") and len(phone) == 12:
        return f"+{phone}"
    if phone.startswith("0") and len(phone) == 11:
        return f"+98{phone[1:]}"
    if phone.startswith("9") and len(phone) == 10:
        return f"+98{phone}"

    return phone