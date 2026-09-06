from django.urls import path

from .views import TransactionDetailView, TransactionListView

urlpatterns = [
    path("transactions/", TransactionListView.as_view(), name="transaction-list"),
    path("transactions/<int:transaction_id>/", TransactionDetailView.as_view(), name="transaction-detail"),
]
