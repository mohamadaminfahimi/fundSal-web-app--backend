# ============================================================
# Stage 1: Builder
# ============================================================
# نصب وابستگی‌ها در این مرحله انجام می‌شود و در ایمیج نهایی فقط
# artifactهای پایتون (site-packages) کپی می‌شوند. این باعث:
#   - کوچک‌تر شدن ایمیج نهایی
#   - حذف build-essential و dev headers از runtime
#   - کاهش سطح حمله (attack surface)
FROM python:3.12-slim AS builder

# جلوگیری از پرسیدن سوال در نصب پکیج‌ها
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# نصب پیش‌نیازهای کامپایل (فقط در این stage)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# کپی فقط فایل‌های requirements (بهبود cache)
COPY requirements/ requirements/

# نصب وابستگی‌های production در user-local
RUN pip install --user --no-cache-dir -r requirements/production.txt

# ============================================================
# Stage 2: Runtime
# ============================================================
FROM python:3.12-slim AS runtime

# جلوگیری از پرسیدن سوال
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# نصب فقط کتابخانه‌های runtime (بدون dev headers)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

# ساخت کاربر غیر-root با UID مشخص
RUN groupadd --gid 1000 appuser \
    && useradd --create-home --uid 1000 --gid appuser appuser

# کپی وابستگی‌های نصب‌شده از builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# تنظیم PATH برای دسترسی به پکیج‌های user-local
ENV PATH=/home/appuser/.local/bin:$PATH \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=8000

WORKDIR /app

# کپی سورس با مالکیت appuser
COPY --chown=appuser:appuser . .

# ساخت دایرکتوری‌های موردنیاز (static, media, logs)
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R appuser:appuser /app/staticfiles /app/media /app/logs

# تغییر به کاربر غیر-root
USER appuser

# پورت اپلیکیشن
EXPOSE 8000

# ============================================================
# Health Check
# ============================================================
# بررسی سلامت Container؛ اگر Django پاسخ ندهد، orchestrator
# (Docker Compose / Kubernetes) Container را unhealthy می‌بیند.
HEALTHCHECK --interval=30s \
    --timeout=5s \
    --start-period=20s \
    --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health/ || exit 1

# ============================================================
# Entrypoint
# ============================================================
# tini به‌عنوان init process:
#   - مدیریت صحیح SIGTERM/SIGINT
#   - جلوگیری از zombie processes
#   - graceful shutdown برای gunicorn
ENTRYPOINT ["/usr/bin/tini", "--"]

# اجرای Gunicorn با تنظیمات production
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--worker-class", "sync", \
     "--worker-tmp-dir", "/dev/shm", \
     "--timeout", "60", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]