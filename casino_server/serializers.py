from rest_framework import serializers
from .models import User, Cryptos, CoinFlip

class CryptoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Cryptos
        fields = ('Symbol', 'Coinid', 'Price')

class UserBalanceSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ('ETH_Amount', 'BNB_Amount')

class CoinFlipSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CoinFlip
        fields = ('id', 'secret_seed', 'nonce', 'is_expired_token', 'straight', 'bet_type', 'bet_amount')
