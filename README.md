# Precious Metals Trading Platform — Backend

Backend یک پلتفرم خرید، فروش و مدیریت طلا/نقره؛ ساخته‌شده با Django + Django
REST Framework + PostgreSQL، به‌صورت Modular Monolith و توسعه‌ی مرحله‌به‌مرحله.

> **وضعیت فعلی:** Phase 0 (معماری) و Phase 1 (راه‌اندازی اولیه پروژه) تکمیل
> شده است. مدل‌های واقعی (User، Wallet، Order و...) در فازهای بعدی اضافه
> می‌شوند.

## معماری

```
backend/
├── config/
│   ├── settings/
│   │   ├── base.py           # تنظیمات مشترک
│   │   ├── development.py    # override برای محیط توسعه
│   │   └── production.py     # override برای محیط تولید + سخت‌سازی امنیتی
│   ├── urls.py                # ریشه‌ی URLConf، نسخه‌بندی‌شده با /api/v1/
│   ├── wsgi.py / asgi.py
├── apps/
│   ├── common/                # کد مشترک بین اپ‌ها (فعلاً فقط اسکلت)
│   ├── users/                 # فاز ۴ و ۵
│   ├── market/                # فاز ۱۳
│   ├── wallet/                # فاز ۸
│   ├── trading/               # فاز ۱۰ و ۱۱
│   ├── transactions/          # فاز ۹
│   └── invoices/              # فاز ۱۲
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── manage.py
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

**چرا Settings به سه فایل تقسیم شده؟** تفاوت‌های بین development و production
(DEBUG، HTTPS، Cookie Security) زیاد و حساس هستند؛ نگه‌داشتن آن‌ها در یک فایل
با شرط `if` ریسک فعال ماندن یک تنظیم ناامن به‌صورت تصادفی در production را
افزایش می‌دهد. جدا کردن فایل‌ها این ریسک را از بین می‌برد.

**چرا apps/ به‌جای اپ‌های تخت (flat) در ریشه‌ی پروژه؟** با رشد پروژه (User،
Wallet، Trading، Invoice و...) نگه‌داشتن مرزهای Domain به‌صورت واضح در یک
پوشه‌ی جداگانه، خواندن و نگهداری پروژه را برای توسعه‌دهنده‌ی بعدی ساده‌تر
می‌کند و مسیر migrate به Microservice را (در صورت نیاز در آینده) باز نگه
می‌دارد.

## نصب و اجرا (Local Development)

### پیش‌نیازها

- Python 3.12+
- PostgreSQL 16+
- (اختیاری) Docker + Docker Compose

### مراحل

```bash
# ۱. ایجاد و فعال‌سازی virtual environment
python3 -m venv .venv
source .venv/bin/activate

# ۲. نصب وابستگی‌های development
pip install -r requirements/development.txt

# ۳. تنظیم متغیرهای محیطی
cp .env.example .env
# سپس مقادیر DJANGO_SECRET_KEY و POSTGRES_* را در .env با مقادیر واقعی خود پر کنید.

# ۴. ایجاد دیتابیس PostgreSQL (اگر از قبل وجود ندارد)
psql -c "CREATE USER trading_platform WITH PASSWORD 'your-password';"
psql -c "CREATE DATABASE trading_platform OWNER trading_platform;"

# ۵. اجرای Migration ها
python manage.py migrate

# ۶. اجرای سرور توسعه
python manage.py runserver
```

پس از اجرا:

- Django Admin: <http://localhost:8000/admin/>
- مستندات API (Swagger UI): <http://localhost:8000/api/v1/docs/>

### توضیح دستورات

| دستور | توضیح |
|---|---|
| `python manage.py migrate` | تمام Migration های تعریف‌شده را روی دیتابیس تنظیم‌شده در `.env` اعمال می‌کند. |
| `python manage.py runserver` | سرور توسعه‌ی Django را اجرا می‌کند (فقط برای local، هرگز در production). |
| `python manage.py check --deploy` | یک Checklist امنیتی برای بررسی آمادگی تنظیمات برای production اجرا می‌کند. |

## اجرا با Docker

```bash
cp .env.example .env   # و مقداردهی صحیح متغیرها
docker compose up --build
```

سرویس `db` (PostgreSQL) و `backend` (Django روی Gunicorn) به‌صورت خودکار
بالا می‌آیند. توضیح کامل‌تر deployment در فاز مربوطه (Phase 23) اضافه
می‌شود.

## متغیرهای محیطی

به فایل [`.env.example`](.env.example) مراجعه کنید؛ تمام متغیرهای لازم و
توضیح هرکدام آنجا مستند شده است.

## تست

```bash
pytest
```

(Test suite واقعی از Phase 19 به بعد به‌تدریج تکمیل می‌شود.)

## نقشه‌ی راه فازها

نگاه کلی به فازهای باقی‌مانده در پیام‌های چت مستند شده و به‌ترتیب پیاده‌سازی
می‌شوند: Custom User → Authentication → Authorization → Core Models →
Wallet → Transactions → Buy/Sell Orders → Invoices → Market Prices →
Caching → Logging → Audit Log → Error Handling → Security Hardening →
Testing → Performance → API Docs → Docker → Deployment → Monitoring →
Security Audit نهایی.
# fundSal-web-app--backend
