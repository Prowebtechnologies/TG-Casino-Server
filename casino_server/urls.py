from django.urls import path
from .views import (
    getPrice,
    getBalance,
    sendMessage
)

urlpatterns = [
    path('price', getPrice),
    path('balance', getBalance),
    path('sendMessage', sendMessage),
]