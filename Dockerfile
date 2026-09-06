# مرحله‌ی builder: وابستگی‌ها را نصب می‌کند بدون این‌که کامپایلرها و ابزارهای
# ساخت (build-essential) در ایمیج نهایی باقی بمانند؛ این باعث کوچک‌تر و
# امن‌تر شدن ایمیج تولید (کاهش سطح حمله) می‌شود.
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --user --no-cache-dir -r requirements/production.txt

# ---------------------------------------------------------------------------

FROM python:3.12-slim AS runtime

# libpq5 (بدون dev headers) برای اتصال زمان اجرا به PostgreSQL کافی است.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    # اجرای اپلیکیشن با یک کاربر غیر-root ریسک را در صورت سوءاستفاده از یک
    # آسیب‌پذیری داخل Container محدود می‌کند (Container Escape سخت‌تر می‌شود).
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /root/.local /home/appuser/.local

WORKDIR /app
COPY --chown=appuser:appuser . .

USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

EXPOSE 8000

# Health check سطح Container؛ اگر Django پاسخ ندهد، Orchestrator (مثل
# Docker Compose یا Kubernetes) متوجه Container ناسالم می‌شود.
# نکته: مسیر /api/v1/health/ در فاز مربوط به Health Check پیاده‌سازی می‌شود؛
# تا آن زمان این HEALTHCHECK همیشه Unhealthy گزارش می‌دهد (بی‌ضرر در این فاز).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/')" || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
