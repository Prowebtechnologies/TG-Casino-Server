from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async
import random
import json
import hashlib
import datetime
import jwt
import requests

from casino_backend.settings import BOT_TOKEN
from casino_backend.asgi import sio
from .serializers import CryptoSerializer, UserBalanceSerializer, CoinFlipSerializer
from .models import Cryptos, User, Slot, CoinFlip

SLOT_REELS = 5
SLOT_REEL_SYMBOLS = 6
CF_WINNING_RATE = 1.98

def generateToken(userId):
    return jwt.encode({
        'user_id': userId,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    }, BOT_TOKEN, algorithm="HS256")

def verifyToken(token):
    try:
        data = jwt.decode(token, BOT_TOKEN, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return False
    return True

def createHash():
    secret_seed = str(random.randint(1, 1000000))
    nonce = str(random.randint(1, 1000000))
    hash_value = hashlib.sha256((secret_seed + nonce).encode()).hexdigest()
    return secret_seed, nonce, hash_value

def generateSymbol():
    return random.choice(range(SLOT_REEL_SYMBOLS))

def generateSlot():
    reels = [generateSymbol() for _ in range(SLOT_REELS)]
    return reels

@api_view(['GET'])
@csrf_exempt
def getPrice(request):
    cryptos = Cryptos.objects.all()
    serializer = CryptoSerializer(cryptos, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@csrf_exempt
def getBalance(request):
    data = json.loads(request.body)
    user_id = data['UserID']
    user = get_object_or_404(User, UserId=user_id)
    result = {}
    serializer = UserBalanceSerializer(user, data=request.data)
    if serializer.is_valid():
        result = {
            "ETH" : serializer.data['ETH_Amount'],
            "BNB" : serializer.data['BNB_Amount'],
        }
        return Response(result)    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@csrf_exempt
def sendMessage(request):
    data = json.loads(request.body)
    user_id = int(data['user_id'])
    message = data['message']
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    if user_id == -1 : #send message to all users
        pass
    else : #send message to specific user
        try :
            msg_data = {
                'chat_id': user_id,
                'text': message,
            }
            response = requests.post(url, data=msg_data)
        except Exception as e:
            print(f'Error in DM : {e}')

print("--------- Server start ----------")

@sio.event
async def connect(sid, environ):
    print('connect :', sid)

@sio.event
async def disconnect(sid):
    print('disconnect :', sid)

@sio.event
async def coinflip(sid, data):
    try :
        cmd = data['cmd']
        user_id = data['user_id']
        coin_type = int(data['coin_type'])
        bet_amount = float(data['bet_amount'])
        server_hash = data['server_hash']
        # user_hash = data['hash']
    except Exception as e:
        print(f"Error in coinflip: {e}")
        return
    user = await sync_to_async(get_object_or_404)(User, UserId=user_id)
    serializer = UserBalanceSerializer(user, data=data)
    if serializer.is_valid():
        match cmd:
            case 'bet':
                betted = False
                if coin_type == 0 and user.ETH_Amount >= bet_amount :
                    user.ETH_Amount -= bet_amount
                    betted = True
                elif coin_type == 1 and user.BNB_Amount >= bet_amount:
                    user.BNB_Amount -= bet_amount
                    betted = True
                if not betted:
                    return

                secret_seed, nonce, server_hash = createHash()
                token = generateToken(user_id)

                bet_data = {
                    'cmd' : 'betted',
                    'user_id': user_id, 
                    'hash': server_hash, 
                    'ETH' : user.ETH_Amount,
                    'BNB' : user.BNB_Amount
                    }
                await sio.emit('coinflip', bet_data, room=sid)
                await sync_to_async(user.save)()
                real_betAmount = bet_amount * 0.95
                coinflip_record = await sync_to_async(CoinFlip.objects.create)(user_id=user_id, server_hash=server_hash, secret_seed=secret_seed, nonce=nonce, parent_id=-1, straight=1, is_expired_token=token, flip_result="", bet_type=coin_type, bet_amount=real_betAmount)
                await sync_to_async(coinflip_record.save)()
            case 'predict':
                coin = data['coin']
                flip_record = await sync_to_async(CoinFlip.objects.get)(server_hash=server_hash)
                # flip_record = await sync_to_async(get_object_or_404)(CoinFlip, server_hash=server_hash)
                # filter_data = {"server_hash" : server_hash}
                # serializer = CoinFlipSerializer(flip_record, data=filter_data)
                # if serializer.is_valid():
                if flip_record:
                    flipId = flip_record.id
                    secret_seed = flip_record.secret_seed
                    nonce = flip_record.nonce
                    token = flip_record.is_expired_token
                    straight = flip_record.straight
                    flip_bet_type = flip_record.bet_type
                    flip_bet_amount = flip_record.bet_amount

                    if verifyToken(token):
                        coinResult = (int(secret_seed) + int(nonce)) % 2
                        flip_result = ''
                        if coinResult == 1:
                            flip_result = 'Heads'
                        else :
                            flip_result = 'Tails'
                        
                        next_server_hash = ''
                        win = coinResult == coin

                        won = 0
                        if win :
                            won = CF_WINNING_RATE ** straight
                            flip_record.win = 1
                            flip_record.is_expire_token = "expired"
                            flip_record.winning_rate = won
                            flip_record.flip_result = flip_result
                            flip_record.server_hash = server_hash
                            await sync_to_async(flip_record.save)()

                            straight = straight + 1
                            next_secret_seed, next_nonce, next_server_hash = createHash()
                            new_token = generateToken(user_id)
                            new_coinflip_record = await sync_to_async(CoinFlip.objects.create)(user_id=user_id, server_hash=next_server_hash, secret_seed=next_secret_seed, nonce=next_nonce, parent_id=flipId, straight=straight, is_expired_token=new_token, flip_result="", bet_type=flip_bet_type, bet_amount=flip_bet_amount)
                            await sync_to_async(new_coinflip_record.save)()
                        
                        else :
                            won = 0
                            flip_record.win = 0
                            flip_record.is_expire_token = "expired"
                            flip_record.winning_rate = won
                            flip_record.flip_result = flip_result
                            flip_record.server_hash = server_hash
                            await sync_to_async(flip_record.save)()

                        bet_data = {
                                "cmd" : "predicted",
                                "user_id" : user_id,
                                "status" : 0,
                                "result" : coinResult,
                                "win" : win,
                                "seed" : secret_seed,
                                "nonce" : nonce,
                                "winning_rate" : won,
                                "next_hash" : next_server_hash
                            }
                        await sio.emit('coinflip', bet_data, room=sid)
                    else:
                        print("Token expired")
                        bet_data = {
                                "cmd" : "predicted",
                                "status" : -2,
                                "user_id" : user_id,
                            }
                        await sio.emit('coinflip', bet_data, room=sid)
                else :
                    print("FlipRecord Not Found")
                    bet_data = {
                            "cmd" : "predicted",
                            "user_id" : user_id,
                            "status" : -1,
                        }
                    await sio.emit('coinflip', bet_data, room=sid)
            case 'cashout':
                flip_record = await sync_to_async(CoinFlip.objects.get)(server_hash=server_hash)
                if flip_record:
                    win = flip_record.win
                    won = flip_record.winning_rate
                    straight = flip_record.straight
                    cashout = flip_record.cashout
                    flip_bet_type = flip_record.bet_type
                    flip_bet_amount = flip_record.bet_amount
                    if cashout == 0 and win == 1:
                        won1 = CF_WINNING_RATE ** straight
                        if won == won1:
                            flip_record.cashout = won1
                            await sync_to_async(flip_record.save)()

                            won_amount = won1 * flip_bet_amount

                            ETH = user.ETH_Amount
                            BNB = user.BNB_Amount
                            if flip_bet_type == 0 :
                                won_amount = won_amount + ETH
                                user.ETH_Amount = won_amount
                            elif flip_bet_type == 1 :
                                won_amount = won_amount + BNB
                                user.BNB_Amount = won_amount
                            await sync_to_async(user.save)()


@sio.event
async def slot(sid, data):
    try :
        cmd = data['cmd']
        user_id = data['user_id']
        coin_type = int(data['coin_type'])
        bet_amount = float(data['bet_amount'])
        # user_hash = data['hash']
    except Exception as e:
        print(f"Error in playSlot: {e}")
        return
    user = await sync_to_async(get_object_or_404)(User, UserId=user_id)
    serializer = UserBalanceSerializer(user, data=data)
    if serializer.is_valid():
        match cmd:
            case 'bet':
                betted = False
                if coin_type == 0 and user.ETH_Amount >= bet_amount :
                    user.ETH_Amount -= bet_amount
                    betted = True
                elif coin_type == 1 and user.BNB_Amount >= bet_amount:
                    user.BNB_Amount -= bet_amount
                    betted = True
                if not betted:
                    return
                slot = generateSlot()
                slot_data = {
                    'cmd' : 'result',
                    'user_id': user_id, 
                    'cashout': random.uniform(0, 9), 
                    'slot' : slot
                    }
                await sio.emit('slot', slot_data, room=sid)
                await sync_to_async(user.save)()
                real_bet = bet_amount * 0.95
                slot_record = await sync_to_async(Slot.objects.create)(user_id=user_id, slot_result=str(slot), bet_type=coin_type, bet_amount=real_bet)
                await sync_to_async(slot_record.save)()

@sio.event
async def plinko(sid, data):
    print('--------------- PlayPlinko : ', sid)
    try :
        cmd         = data['cmd']
        user_id     = data['user_id']
        coin_type   = int(data['coin_type'])
        bet_amount  = float(data['bet_amount'])
        rate        = float(data['rate'])
        # user_hash = data['hash']
    except Exception as e:
        print(f"Error in playSlot: {e}")
        return
    user = await sync_to_async(get_object_or_404)(User, UserId=user_id)
    serializer = UserBalanceSerializer(user, data=data)
    if serializer.is_valid():
        match cmd:
            case 'start':
                betted = False
                if coin_type == 0 and user.ETH_Amount >= bet_amount :
                    user.ETH_Amount -= bet_amount
                    betted = True
                elif coin_type == 1 and user.BNB_Amount >= bet_amount:
                    user.BNB_Amount -= bet_amount
                    betted = True
                if not betted:
                    return
                await sync_to_async(user.save)()
            case 'end':
                winAmount = bet_amount * 0.95 * rate
                if coin_type == 0 :
                    user.ETH_Amount += winAmount
                elif coin_type == 1 :
                    user.BNB_Amount += winAmount
                end_data = {
                    'cmd' : 'end',
                    'user_id': user_id, 
                    'ETH': user.ETH_Amount, 
                    'BNB': user.BNB_Amount,     
                }
                await sio.emit('plinko', end_data, room=sid)
                await sync_to_async(user.save)()

# @sio.on('connect',)
# def connect(sid, environ):
#     print('connect :', sid)

# @sio.on('disconnect')
# def disconnect(sid):
#     print('disconnect :', sid)

# @sio.on('slot')
# def playSlot(sid, data):
