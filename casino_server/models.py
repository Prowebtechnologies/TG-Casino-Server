from django.db import models

class User(models.Model):
    Hash            = models.CharField(max_length=100, null=True, blank=True)
    RealName        = models.CharField(max_length=100, null=True, blank=True)
    UserName        = models.CharField(max_length=100, null=True, blank=True)
    UserId          = models.BigIntegerField()    
    Wallet          = models.CharField(max_length=42, null=True, blank=True)
    ETH_Wagered     = models.FloatField(default=0)
    BNB_Wagered     = models.FloatField(default=0)
    TOKEN_Wagered   = models.FloatField(default=0)
    ETH_Wins        = models.FloatField(default=0)
    BNB_Wins        = models.FloatField(default=0)
    Token_Wins      = models.FloatField(default=0)
    ETH_Amount      = models.FloatField(default=0)
    BNB_Amount      = models.FloatField(default=0)
    Token_Amount    = models.FloatField(default=0)
    JoinDate        = models.DateTimeField(auto_now_add=True)
    UserAllowed     = models.BooleanField(default=True)
    Deployed_ETH    = models.BooleanField(default=False)
    ReadyTransfer   = models.BooleanField(default=False)
    Deployed_BNB    = models.BooleanField(default=False)
    Role            = models.IntegerField(default=0)
    class Meta:
        db_table = 'tbl_users'
    
    def __int__(self):
        return self.UserId if self.UserId else self.id

class Cryptos(models.Model):
    Symbol = models.CharField(max_length=50, blank=True, null=True)
    Coinid = models.CharField(max_length=50, blank=True, null=True)
    Price  = models.FloatField(default=0)
    class Meta:
        db_table = 'tbl_cryptos'
    
    def __int__(self):
        return self.Symbol if self.Symbol else self.id

class CoinFlip(models.Model):
    user_id             = models.BigIntegerField()
    server_hash         = models.CharField(max_length=255)
    secret_seed         = models.CharField(max_length=10)
    nonce               = models.CharField(max_length=10)
    parent_id           = models.BigIntegerField(default=-1)
    straight            = models.IntegerField(default=0)
    is_expired_token    = models.CharField(max_length=255, null=True, blank=True)
    flip_result         = models.CharField(max_length=5, null=True, default='')
    win                 = models.BooleanField(default=False)
    winning_rate        = models.FloatField(default=0.0)
    cashout             = models.FloatField(default=0.0)
    bet_type            = models.IntegerField(default=0)
    bet_amount          = models.FloatField(default=0.0)
    bet_time            = models.DateTimeField(auto_now_add=True, null=True, blank=False)
    class Meta:
        db_table = 'tbl_coinflip'
    
    def __int__(self):
        return self.user_id if self.user_id else self.id

class Slot(models.Model):
    user_id             = models.BigIntegerField()
    server_hash         = models.CharField(max_length=255, null=True, blank=False)
    secred_seed         = models.CharField(max_length=10, null=True, blank=False)
    nonce               = models.CharField(max_length=10, null=True, blank=False)
    slot_result         = models.CharField(max_length=20, null=True, default='')
    win                 = models.BooleanField(default=False)
    cashout             = models.FloatField(default=0.0)
    bet_type            = models.IntegerField(default=0)
    bet_amount          = models.FloatField(default=0.0)
    bet_time            = models.DateTimeField(auto_now_add=True, null=True, blank=False)
    class Meta:
        db_table = 'tbl_slot'
    
    def __int__(self):
        return self.user_id if self.user_id else self.id

class Ads(models.Model):
    UserID      = models.BigIntegerField(null=True, blank=True)
    Url         = models.CharField(max_length=255, null=True, blank=True)
    Content     = models.CharField(max_length=255, null=True, blank=True)
    Time        = models.IntegerField(null=True, blank=True)
    Duration    = models.IntegerField(null=True, blank=True)
    Expired     = models.BooleanField(default=True)
    StarTime    = models.DateTimeField(null=True, blank=True)
    CreatedAt   = models.DateTimeField(auto_now_add=True, null=True)
    ExpiredAt   = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = 'tbl_ads'
    
    def __int__(self):
        return self.UserID if self.UserID else self.id