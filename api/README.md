# راهنمای استفاده از API

این فایل قرارداد فعلی API پروژه را توضیح می‌دهد تا بتوانید آن را در فرانت‌اند
(برای مثال Next.js، React یا هر کلاینت دیگری) استفاده کنید.

## آدرس پایه

در محیط محلی:

```text
http://localhost:8000/api/v1
```

در محیط production باید دامنه‌ی واقعی backend جایگزین `localhost:8000` شود.
تمام مسیرهای این مستندات نسبت به آدرس پایه نوشته شده‌اند. برای نمونه، مسیر
ثبت‌نام برابر است با:

```text
POST http://localhost:8000/api/v1/auth/register/
```

مستندات تعاملی Swagger نیز در آدرس زیر در دسترس است:

```text
http://localhost:8000/api/v1/docs/
```

## نکته‌ی مهم احراز هویت

احراز هویت این API با JWT و cookie انجام می‌شود. بعد از ورود، backend دو cookie
به نام‌های زیر ارسال می‌کند:

- `access_token`: برای درخواست‌های احراز هویت‌شده، با عمر حدود ۱۵ دقیقه
- `refresh_token`: برای گرفتن access token جدید، با عمر حدود ۷ روز

این cookieها `HttpOnly` هستند؛ بنابراین کد JavaScript فرانت‌اند نباید و نمی‌تواند
مقدار آن‌ها را بخواند. توکن را در `localStorage` یا `sessionStorage` ذخیره نکنید.

برای ارسال cookie در `fetch` حتماً از `credentials: "include"` استفاده کنید:

```javascript
const response = await fetch("http://localhost:8000/api/v1/auth/profile/", {
  method: "GET",
  credentials: "include",
  headers: {
    Accept: "application/json",
  },
});

const result = await response.json();
```

برای Axios:

```javascript
import axios from "axios";

export const api = axios.create({
  baseURL: "http://localhost:8000/api/v1",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});
```

فرانت‌اند باید روی origin مجاز تنظیم‌شده در `CORS_ALLOWED_ORIGINS` اجرا شود؛ در
حالت محلی پروژه، origin پیش‌فرض `http://localhost:3000` است.

## قالب عمومی پاسخ‌ها

### پاسخ موفق

اکثر endpointها پاسخ موفق را به شکل زیر برمی‌گردانند:

```json
{
  "success": true,
  "data": {}
}
```

مقدار `data` بسته به endpoint می‌تواند object، array یا message باشد.

### پاسخ خطا

خطاهای business معمولاً به شکل زیر هستند:

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "INSUFFICIENT_BALANCE"
  }
}
```

خطاهای اعتبارسنجی Django REST Framework ممکن است به‌جای این ساختار، فیلدهای
اعتبارسنجی را برگردانند. فرانت‌اند همیشه باید ابتدا `response.ok` یا status code
را بررسی کند و سپس بدنه‌ی JSON را بخواند.

کدهای مهم HTTP:

| کد | معنی |
|---|---|
| `200` | درخواست با موفقیت انجام شد |
| `201` | منبع جدید ساخته شد؛ مانند ثبت سفارش یا ثبت‌نام |
| `400` | داده‌ی ورودی نامعتبر یا خطای business |
| `401` | کاربر وارد نشده، cookie وجود ندارد یا منقضی شده است |
| `404` | منبع موردنظر پیدا نشد |
| `405` | متد HTTP برای آن endpoint مجاز نیست |

## فهرست کامل endpointها

| متد | مسیر | احراز هویت | کاربرد |
|---|---|---:|---|
| `GET` | `/health/` | خیر | بررسی سلامت backend |
| `POST` | `/auth/register/` | خیر | ثبت‌نام کاربر |
| `POST` | `/auth/login/` | خیر | ورود و ساخت cookieهای JWT |
| `POST` | `/auth/logout/` | بله | خروج و حذف cookieها |
| `POST` | `/auth/refresh/` | refresh cookie | تمدید access token |
| `GET` | `/auth/profile/` | بله | دریافت پروفایل کاربر |
| `PATCH` | `/auth/profile/` | بله | ویرایش پروفایل کاربر |
| `GET` | `/wallet/` | بله | دریافت کیف پول |
| `GET` | `/wallet/assets/` | بله | دریافت دارایی‌های فلزی |
| `POST` | `/wallet/adjust/` | بله | افزایش یا کاهش موجودی کیف پول |
| `GET` | `/transactions/` | بله | دریافت تراکنش‌های کاربر |
| `GET` | `/transactions/{id}/` | بله | دریافت جزئیات یک تراکنش |
| `GET` | `/trading/orders/` | بله | دریافت سفارش‌های کاربر |
| `POST` | `/trading/orders/buy/` | بله | ثبت سفارش خرید |
| `POST` | `/trading/orders/sell/` | بله | ثبت سفارش فروش |
| `GET` | `/schema/` | خیر | دریافت OpenAPI schema |
| `GET` | `/docs/` | خیر | مشاهده‌ی Swagger UI |

## ۱. سلامت سرویس

### `GET /health/`

برای health check، load balancer یا بررسی در دسترس بودن backend استفاده می‌شود.

نمونه پاسخ:

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "gold-app-backend"
  }
}
```

## ۲. ثبت‌نام

### `POST /auth/register/`

بدون نیاز به ورود است.

بدنه‌ی درخواست:

```json
{
  "email": "user@example.com",
  "first_name": "Ali",
  "last_name": "Ahmadi",
  "phone_number": "+989121234567",
  "password": "A-strong-password-123"
}
```

قوانین مهم:

- `email` اجباری و یکتا است.
- `password` حداقل ۱۰ کاراکتر است و password validatorهای Django را رد می‌کند.
- `first_name` و `last_name` اختیاری هستند.
- `phone_number` اختیاری است و باید فرمت بین‌المللی داشته باشد؛ نمونه:
  `+989121234567`.

نمونه پاسخ `201`:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "Ali",
    "last_name": "Ahmadi",
    "phone_number": "+989121234567",
    "is_email_verified": false,
    "date_joined": "2026-09-07T12:00:00Z"
  }
}
```

ثبت‌نام به‌تنهایی کاربر را وارد سیستم نمی‌کند؛ برای دریافت cookie باید login
انجام شود.

## ۳. ورود

### `POST /auth/login/`

بدون نیاز به ورود است.

بدنه‌ی درخواست:

```json
{
  "email": "user@example.com",
  "password": "A-strong-password-123"
}
```

در صورت موفقیت، پاسخ شامل اطلاعات کاربر است و backend با headerهای `Set-Cookie`
، cookieهای `access_token` و `refresh_token` را تنظیم می‌کند.

نمونه استفاده در فرانت:

```javascript
await api.post("/auth/login/", {
  email: "user@example.com",
  password: "A-strong-password-123",
});

// نیازی به ذخیره یا خواندن token نیست.
// مرورگر cookieهای HttpOnly را نگه می‌دارد.
```

نمونه پاسخ:

```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "first_name": "Ali",
      "last_name": "Ahmadi",
      "phone_number": "+989121234567",
      "is_email_verified": false,
      "date_joined": "2026-09-07T12:00:00Z"
    },
    "access_expires_at": "2026-09-07T12:15:00Z"
  }
}
```

## ۴. خروج

### `POST /auth/logout/`

نیازمند access cookie معتبر است.

```javascript
await api.post("/auth/logout/");
```

نمونه پاسخ:

```json
{
  "success": true,
  "data": {
    "message": "خروج با موفقیت انجام شد."
  }
}
```

backend cookieهای احراز هویت را حذف می‌کند.

## ۵. تمدید access token

### `POST /auth/refresh/`

این endpoint به access token نیاز ندارد، اما باید `refresh_token` cookie معتبر در
درخواست وجود داشته باشد.

```javascript
await api.post("/auth/refresh/");
```

در صورت موفقیت، cookieهای جدید تنظیم می‌شوند و پاسخ شامل access token است. چون
فرانت به cookie دسترسی ندارد، کافی است فقط درخواست را با
`withCredentials: true` ارسال کند.

خطاهای مهم:

- `REFRESH_TOKEN_MISSING`: refresh cookie ارسال نشده است.
- `INVALID_REFRESH_TOKEN`: refresh token نامعتبر یا منقضی است.

## ۶. پروفایل کاربر

### `GET /auth/profile/`

اطلاعات کاربر واردشده را برمی‌گرداند.

### `PATCH /auth/profile/`

فقط فیلدهای زیر قابل ویرایش هستند:

```json
{
  "first_name": "Reza",
  "last_name": "Karimi",
  "phone_number": "+989121234567"
}
```

فیلدهای `email`، `id` و `is_email_verified` از این endpoint قابل تغییر نیستند.

## ۷. کیف پول

### `GET /wallet/`

نمونه پاسخ:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "user": 1,
    "available_balance": "1000000.00",
    "pending_balance": "250000.00",
    "total_balance": "1250000.00",
    "currency": "IRR",
    "created_at": "2026-09-07T12:00:00Z",
    "updated_at": "2026-09-07T12:00:00Z"
  }
}
```

تمام مقدارهای مالی به‌صورت string ارسال می‌شوند تا دقت اعشاری در JavaScript از
بین نرود. برای محاسبات پولی از `number` معمولی استفاده نکنید.

### `GET /wallet/assets/`

نمونه پاسخ:

```json
{
  "success": true,
  "data": [
    {
      "id": 4,
      "user": 1,
      "metal_code": "GOLD",
      "available_quantity": "2.5000",
      "locked_quantity": "0.5000",
      "total_quantity": "3.0000",
      "created_at": "2026-09-07T12:00:00Z",
      "updated_at": "2026-09-07T12:00:00Z"
    }
  ]
}
```

### `POST /wallet/adjust/`

این endpoint برای adjustment مدیریتی است و بدنه‌ی زیر را می‌گیرد:

افزایش موجودی:

```json
{
  "action": "credit",
  "amount": "1000000.00"
}
```

کاهش موجودی:

```json
{
  "action": "debit",
  "amount": "250000.00"
}
```

مقدار `action` فقط می‌تواند `credit` یا `debit` باشد. برای مقدار نامعتبر، خطای
`INVALID_ACTION` برمی‌گردد.

## ۸. تراکنش‌ها

### `GET /transactions/`

تراکنش‌های کاربر را از جدیدترین به قدیمی‌ترین برمی‌گرداند.

نمونه پاسخ:

```json
{
  "success": true,
  "data": [
    {
      "id": 10,
      "user": 1,
      "transaction_type": "buy_order",
      "amount": "250000.00",
      "currency": "IRR",
      "status": "pending",
      "reference_id": "buy-order-5",
      "metadata": {
        "order_id": 5,
        "metal_code": "GOLD"
      },
      "created_at": "2026-09-07T12:00:00Z",
      "updated_at": "2026-09-07T12:00:00Z"
    }
  ]
}
```

مقادیر `transaction_type` فعلی:

```text
deposit, withdrawal, buy_order, sell_order, fee, adjustment
```

مقادیر `status` فعلی:

```text
pending, completed, failed, reversed
```

### `GET /transactions/{transaction_id}/`

برای نمونه:

```text
GET /transactions/10/
```

اگر تراکنش متعلق به کاربر نباشد یا وجود نداشته باشد، پاسخ `404` با کد
`NOT_FOUND` برمی‌گردد.

## ۹. سفارش‌های معاملاتی

### `GET /trading/orders/`

تمام سفارش‌های کاربر را از جدیدترین به قدیمی‌ترین برمی‌گرداند.

فیلدهای مهم سفارش:

| فیلد | توضیح |
|---|---|
| `metal_code` | کد فلز، مانند `GOLD` یا `SILVER` |
| `side` | جهت سفارش: `buy` یا `sell` |
| `order_type` | در حال حاضر سفارش‌ها با مقدار `limit` ساخته می‌شوند |
| `quantity` | مقدار فلز، با حداکثر ۴ رقم اعشار |
| `price_per_gram` | قیمت هر گرم، با حداکثر ۴ رقم اعشار |
| `total_amount` | مبلغ کل محاسبه‌شده توسط backend |
| `status` | وضعیت سفارش |
| `idempotency_key` | کلید جلوگیری از ثبت تکراری سفارش |

مقادیر `status`:

```text
pending, partially_filled, filled, cancelled, rejected
```

## ۱۰. ثبت سفارش خرید

### `POST /trading/orders/buy/`

بدنه‌ی درخواست:

```json
{
  "metal_code": "GOLD",
  "quantity": "2.5000",
  "price_per_gram": "1000000.0000",
  "idempotency_key": "buy-GOLD-20260907-0001"
}
```

نکات مهم:

- `quantity` باید بزرگ‌تر از صفر باشد.
- `price_per_gram` باید بزرگ‌تر از صفر باشد.
- `idempotency_key` اجباری است و باید برای هر عملیات جدید یکتا باشد.
- اگر همان کاربر دوباره همان `idempotency_key` را بفرستد، سفارش قبلی برگردانده
  می‌شود و سفارش تکراری ساخته نمی‌شود.
- موجودی قابل استفاده‌ی کیف پول باید برای مبلغ کل کافی باشد.
- `total_amount` از ضرب quantity در price محاسبه می‌شود؛ آن را از فرانت ارسال
  نکنید.

نمونه پاسخ `201`:

```json
{
  "success": true,
  "data": {
    "id": 5,
    "user": 1,
    "metal_code": "GOLD",
    "side": "buy",
    "order_type": "limit",
    "quantity": "2.5000",
    "remaining_quantity": "2.5000",
    "price_per_gram": "1000000.0000",
    "total_amount": "2500000.00",
    "idempotency_key": "buy-GOLD-20260907-0001",
    "status": "pending",
    "metadata": {},
    "created_at": "2026-09-07T12:00:00Z",
    "updated_at": "2026-09-07T12:00:00Z"
  }
}
```

خطاهای business:

- `IDEMPOTENCY_KEY_REQUIRED`: کلید ارسال نشده است.
- `INSUFFICIENT_BALANCE`: موجودی کیف پول کافی نیست.
- `INVALID_REQUEST`: داده‌ی ارسالی نامعتبر است.

## ۱۱. ثبت سفارش فروش

### `POST /trading/orders/sell/`

بدنه‌ی درخواست مشابه خرید است:

```json
{
  "metal_code": "GOLD",
  "quantity": "0.5000",
  "price_per_gram": "1000000.0000",
  "idempotency_key": "sell-GOLD-20260907-0001"
}
```

برای فروش، کاربر باید به اندازه‌ی کافی از همان `metal_code` در دارایی قابل دسترس
خود داشته باشد. در زمان ثبت سفارش، مقدار دارایی قفل می‌شود.

خطاهای business:

- `IDEMPOTENCY_KEY_REQUIRED`: کلید ارسال نشده است.
- `INSUFFICIENT_ASSET`: مقدار فلز کافی نیست.
- `INVALID_REQUEST`: داده‌ی ارسالی نامعتبر است.

## الگوی پیشنهادی برای کلاینت فرانت

یک wrapper مرکزی برای API بسازید تا تنظیمات cookie، parsing پاسخ و خطاها در همه‌ی
صفحات تکرار نشود:

```javascript
const API_URL = "http://localhost:8000/api/v1";

export async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  const result = await response.json().catch(() => null);

  if (!response.ok) {
    const error = new Error(
      result?.error?.message || result?.detail || "خطا در ارتباط با سرور",
    );
    error.status = response.status;
    error.code = result?.error?.code;
    error.payload = result;
    throw error;
  }

  return result;
}

export function login(email, password) {
  return request("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getWallet() {
  return request("/wallet/");
}

export function createBuyOrder(data) {
  return request("/trading/orders/buy/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
```

## رفتار پیشنهادی هنگام `401`

1. اگر پاسخ یک endpoint `401` بود، یک بار `POST /auth/refresh/` را صدا بزنید.
2. اگر refresh موفق بود، درخواست اصلی را فقط یک بار تکرار کنید.
3. اگر refresh هم `401` داد، cookieها معتبر نیستند؛ کاربر را به صفحه‌ی login
   منتقل کنید.
4. از retry بی‌نهایت جلوگیری کنید.

نمونه‌ی ساده با Axios interceptor:

```javascript
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retried) {
      originalRequest._retried = true;
      await api.post("/auth/refresh/");
      return api(originalRequest);
    }

    return Promise.reject(error);
  },
);
```

## نکات مربوط به CSRF و CORS

- چون authentication با cookie انجام می‌شود، `credentials: "include"` در fetch
  یا `withCredentials: true` در Axios لازم است.
- origin فرانت باید در `CORS_ALLOWED_ORIGINS` backend ثبت شده باشد.
- در production باید HTTPS فعال باشد و تنظیمات cookie و CSRF با دامنه‌ی واقعی
  هماهنگ شوند.
- برای درخواست‌های تغییر‌دهنده‌ی داده مانند `POST` و `PATCH`، اگر محیط شما
  بررسی CSRF را فعال کند، فرانت باید CSRF token را نیز طبق تنظیمات deployment
  ارسال کند.

## نکات مالی و نوع داده‌ها

- مقدارهای پولی و مقدار فلز با دقت اعشاری ارسال می‌شوند و در JSON معمولاً string
  هستند.
- برای نمایش از تبدیل کنترل‌شده استفاده کنید؛ برای محاسبات مالی از floating
  point معمولی استفاده نکنید.
- `total_amount`، `total_balance` و مقدارهای status را backend تعیین می‌کند.
- قبل از نمایش نتیجه‌ی سفارش، به `status` و `remaining_quantity` توجه کنید؛ ثبت
  سفارش به معنی تکمیل معامله نیست.

## وضعیت فعلی API

این مستندات بر اساس endpointهای فعلی نسخه‌ی `v1` نوشته شده است. endpointهای
قیمت بازار، invoice، پرداخت و لغو سفارش در registry فعلی API وجود ندارند و نباید
از سمت فرانت با فرض وجود آن‌ها فراخوانی شوند.
