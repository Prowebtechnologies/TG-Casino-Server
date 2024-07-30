import random
import json
import threading
import sys
import re
import requests
import pytz
from tzlocal import get_localzone
#******For Test********#
# from db import (
from libs.db import (
    updateSetStrWhereStr,
    updateSetFloatWhereStr,
    readFieldsWhereStr,
    getTopFieldsByLimit,
    insertInitialCoinInfos,
    insertFields
)
from urllib.request import urlopen
from urllib.error import URLError
import datetime
from dotenv.main import load_dotenv
import os

load_dotenv()   

OWNER_ADDRESS = os.environ['OWNER_ADDRSS']
OWNER_PRIVATE_KEY = os.environ['OWNER_PRIVATE_KEY']
CONTRACT_ADDRESS = os.environ['ETH_CONTRACT_ADDRESS']
ETH_TESTNET_ID = os.environ['ETH_TESTNET_ID']
ETH_MAINNET_ID = os.environ['ETH_MAINNET_ID']

HOUSE_CUT_FEE = 50
PERCENTAGE = 1000

ETH_FIXED_WITHDRAW_FEE = float(1)
BSC_FIXED_WITHDRAW_FEE = float(0.3)

async def getPricefromAmount(amount : float, kind : int) -> float:
    value = 0
    if kind == 0 :
        price = await readFieldsWhereStr('tbl_cryptos', 'Price', "Symbol='eth'")
        price = price[0][0]
        value = amount * price
    elif kind == 1 :
        price = await readFieldsWhereStr('tbl_cryptos', 'Price', "Symbol='bnb'")
        price = price[0][0]
        value = amount * price
    elif kind == 2 :
        price = await readFieldsWhereStr('tbl_cryptos', 'Price', "Symbol='token'")
        price = price[0][0]
        print('price', price)
        value = amount * price
    return value

def isValidAddress(w3: any, address: str) -> bool:
    return w3.isAddress(address)

def isValidContractOrWallet(w3: any, address: str) -> bool:
    return isValidAddress(w3, address) and (len(address) == 42 or len(address) == 40)

def isFloat(amount: str) -> bool:
    try:
        float(amount)
        return True
    except ValueError:
        return False

def truncDecimal(value: float, dec: int = 2) -> str:
    return '{:.2f}'.format(value)

def truncDecimal7(value: float) -> str:
    trimStr = '{:.7f}'.format(value)
    return trimStr.rstrip('0').rstrip('.')

def isValidUrl(url) -> bool:
    res = True

    httpsPattern = re.compile(r'^https?://\S+$')
    isHttps = bool(httpsPattern.match(url))

    httpPattern = re.compile(r'^http?://\S+$')
    isHttp = bool(httpPattern.match(url))

    res = isHttps or isHttp

    return res

def isOpenedUrl(url) -> bool:
    try:
        response = requests.get(url)
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        print("HTTP error occurred: ", e)
        print("Status code:", response.status_code)
        print("Reason:", response.reason)
        return True
    except requests.exceptions.ConnectionError as e:
        print("Error connecting: ", e)
        return False
    except requests.exceptions.Timeout as e:
        print("Timeout error: ", e)
        return False
    except requests.exceptions.RequestException as e:
        print("An error occurred: ", e)
        return False

def getUnitString(kind: int) -> str:
    str = ""
    if kind == 0 :
        str = "ETH"
    elif kind == 1:
        str = "BNB"
    return str

async def getWallet(userId: str, userName: str, fullName: str, isBot: bool, ethContract: any) -> str:
    kind = "UserName='{}' AND UserID='{}'".format(userName, userId)
    wallet = await readFieldsWhereStr('tbl_users', 'Wallet', kind)

    # if wallet field is empty, estimate wallet address by salt
    if len(wallet) < 1:
        bytecode = ethContract.functions.getBytecode(OWNER_ADDRESS).call()
        wallet = ethContract.functions.getAddress(bytecode, int(userId)).call()
        field = {
            "RealName": fullName,
            "UserName": userName,
            "UserID": userId,
            "Wallet": wallet,
            "UserAllowed": not isBot,
            "JoinDate": datetime.datetime.now()
        }
        
        await insertFields('tbl_users', field)
    else:
        wallet = wallet[0][0]

    return wallet

async def getBalance(address: str, web3: any, userId: str) -> float:
    nBalance = 0
    
    chain_id = web3.eth.chain_id
    
    balance = None
    kind = "UserID='{}'".format(userId)
    if chain_id == int(ETH_TESTNET_ID):
        balance = await readFieldsWhereStr('tbl_users', 'ETH_Amount', kind)
    else:
        balance = await readFieldsWhereStr('tbl_users', 'BNB_Amount', kind)

    nBalance = balance[0][0]
    return nBalance

async def deploySmartContract(web3: any, contract: any, userId: str) -> bool:
    bResult = False
    try:
        nonce = web3.eth.getTransactionCount(OWNER_ADDRESS)
        chain_id = web3.eth.chain_id

        field = ""
        call_function = None
        if chain_id == int(ETH_TESTNET_ID):
            field = "Deployed_ETH"
            call_function = contract.functions.deploy(int(userId)).buildTransaction({
                "chainId": chain_id,
                "from": OWNER_ADDRESS,
                "nonce": nonce
            })
        else:
            field= "Deployed_BSC"
            call_function = contract.functions.deploy(int(userId)).buildTransaction({
                "chainId": chain_id,
                "from": OWNER_ADDRESS,
                "nonce": nonce,
                "gas": 500000,
                "gasPrice": web3.toWei('10', 'gwei')
            })

        signed_tx = web3.eth.account.sign_transaction(call_function, private_key=OWNER_PRIVATE_KEY)
        send_tx = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        tx_receipt = web3.eth.wait_for_transaction_receipt(send_tx)
        
        bResult = await updateSetFloatWhereStr("tbl_users", field, True, "UserID", userId)
        print("Smart Contract deployed sucessfully")
    except:
        bResult = False
        print("Deploy error")
    return bResult

async def transferAssetsToContract(address: str, web3: any, userId: str) -> bool:
    bResult = False
    try:
        nonce = web3.eth.getTransactionCount(OWNER_ADDRESS)
        chain_id = web3.eth.chain_id

        abi = []
        with open("./abi/custodial_wallet_abi.json") as f:
            abi = json.load(f)
        
        contract = web3.eth.contract(address=address, abi=abi)

        call_function = None
        if chain_id == int(ETH_TESTNET_ID):
            call_function = contract.functions.withdraw(CONTRACT_ADDRESS).buildTransaction({
                "chainId": chain_id,
                "from": OWNER_ADDRESS,
                "nonce": nonce
            })
        else:
            call_function = contract.functions.withdraw(CONTRACT_ADDRESS).buildTransaction({
                "chainId": chain_id,
                "from": OWNER_ADDRESS,
                "nonce": nonce,
                "gas": 1000000,
                "gasPrice": web3.toWei('10', 'gwei')
            })

        signed_tx = web3.eth.account.sign_transaction(call_function, private_key=OWNER_PRIVATE_KEY)
        send_tx = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        tx_receipt = web3.eth.wait_for_transaction_receipt(send_tx)

        log = tx_receipt['logs']
        raw_data = log[0]['data']

        amount = int(str(raw_data)[-64:], 16)

        field = ""
        if chain_id == int(ETH_TESTNET_ID):
            field = "ETH_Amount"
        else:
            field = "BNB_Amount"

        amount = float(amount / (10 ** 18))

        kind = "UserID='{}'".format(userId)
        originalAmount = await readFieldsWhereStr('tbl_users', field, kind)

        amount += float(originalAmount[0][0])
        bResult = await updateSetFloatWhereStr("tbl_users", field, amount, "UserID", userId)

        print("Assets transferred sucessfully")
    except:
        bResult = False
        print("Transfer error")
    return bResult

async def withdrawAmount(web3: any, contract: any, withdrawalAddress: str, amount: float, userId: str) -> dict:
    res = {}
    try:
        nonce = web3.eth.getTransactionCount(OWNER_ADDRESS)
        chain_id = web3.eth.chain_id

        call_function = None
        field = ""

        fee = 0
        if chain_id == int(ETH_TESTNET_ID):
            fee = await calculateTotalWithdrawFee(web3, amount, 0)
            call_function = contract.functions.withdraw(withdrawalAddress, web3.toWei(amount - fee, 'ether')).buildTransaction({
                "chainId": chain_id,
                "from": OWNER_ADDRESS,
                "nonce": nonce
            })
            field = "ETH_Amount"
        else:
            fee = await calculateTotalWithdrawFee(web3, amount, 1)
            call_function = contract.functions.withdraw(withdrawalAddress, web3.toWei(amount - fee, 'ether')).buildTransaction({
                "chainId": chain_id,
                "from": OWNER_ADDRESS,
                "nonce": nonce,
                "gas": 1000000,
                "gasPrice": web3.toWei('10', 'gwei')
            })
            field = "BNB_Amount"
        
        signed_tx = web3.eth.account.sign_transaction(call_function, private_key=OWNER_PRIVATE_KEY)
        send_tx = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        tx_receipt = web3.eth.wait_for_transaction_receipt(send_tx)

        kind = "UserID='{}'".format(userId)
        originalAmount = await readFieldsWhereStr('tbl_users', field, kind)

        amount = float(originalAmount[0][0]) - amount

        bResult = await updateSetFloatWhereStr("tbl_users", field, amount, "UserID", userId)

        res = tx_receipt
    except:
        print("withdraw error")
        return res
    return res

async def withdrawTokenAmount(web3: any, contract: any, token: str, withdrawalAddress: str, amount: float, userId: str, mode: int) -> dict:
    res = {}
    try:
        nonce = web3.eth.getTransactionCount(OWNER_ADDRESS)
        chain_id = web3.eth.chain_id

        call_function = None
        field = ""

        fee = await calculateTotalWithdrawFee(web3, amount, mode)
        call_function = contract.functions.withdrawCustomToken(token, withdrawalAddress, web3.toWei(amount - fee, 'ether')).buildTransaction({
            "chainId": chain_id,
            "from": OWNER_ADDRESS,
            "nonce": nonce
        })
        field = "Token_Amount"
        
        signed_tx = web3.eth.account.sign_transaction(call_function, private_key=OWNER_PRIVATE_KEY)
        send_tx = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        tx_receipt = web3.eth.wait_for_transaction_receipt(send_tx)

        kind = "UserID='{}'".format(userId)
        originalAmount = await readFieldsWhereStr('tbl_users', field, kind)

        amount = float(originalAmount[0][0]) - amount

        bResult = await updateSetFloatWhereStr("tbl_users", field, amount, "UserID", userId)

        res = tx_receipt
    except:
        print("withdraw error")
        return res
    return res

async def calculateTotalWithdrawFee(web3: any, amount: float, mode: int) -> float:
    res = float(0)
    try:
        withdrawalFee = await calculateFixedFee(web3, mode)

        fee = (amount * HOUSE_CUT_FEE / PERCENTAGE) + withdrawalFee
        feeStr = '{:.5f}'.format(fee).rstrip('0')
        
        res = float(feeStr)
    except:
        print("Calculate fee error")
        return res
    return res

async def calculateFixedFee(web3: any, mode: int) -> float:
    res = float(0)
    try:
        print(mode)
        price = 0
        if mode == 0:
            price = await readFieldsWhereStr('tbl_cryptos', 'Price', "Symbol='eth'")
            price = price[0][0]

            res = ETH_FIXED_WITHDRAW_FEE / float(price)
        elif mode == 1:
            price = await readFieldsWhereStr('tbl_cryptos', 'Price', "Symbol='bnb'")
            price = price[0][0]

            res = BSC_FIXED_WITHDRAW_FEE / float(price)
        elif mode == 2:
            price = await readFieldsWhereStr('tbl_cryptos', 'Price', "Symbol='token'")
            price = price[0][0]

            res = ETH_FIXED_WITHDRAW_FEE / float(price)

        feeStr = '{:.5f}'.format(res).rstrip('0')
        
        res = float(feeStr)
    except:
        print("Calculate Fixed fee error")
        return res
    return res

async def getTokenPrice(tokenMode: int) -> float:
    res = float(0)
    try:
        if tokenMode == 0:
            price = await readFieldsWhereStr('tbl_cryptos', 'Price', "Symbol='eth'")
            res = float(price[0][0])
        else:
            price = await readFieldsWhereStr('tbl_cryptos', 'Price', "Symbol='bnb'")
            res = float(price[0][0])

    except:
        print("Get Token Price error")
        return res
    return res

async def calculateCryptoAmountByUSD(amount: float, tokenMode: int) -> float:
    res = float(0)
    try:
        tokenPrice = await getTokenPrice(tokenMode)
        cryptoAmount = amount / tokenPrice
        res = '{:.5f}'.format(cryptoAmount).rstrip('0').rstrip('.')
        res = float(res)

    except:
        print("Calculate Crypto amount by USD amount error")
        return res
    return res

async def createAds(userId: str, link: str, content: str, time: int, duration: int, tokenMode: int, amount: float) -> bool:
    res = False
    try:
        current_utc_time = datetime.datetime.now(pytz.utc)

        booked_utc_time = current_utc_time.replace(hour=time, minute=0, second=0)

        if booked_utc_time < current_utc_time:
            booked_utc_time = booked_utc_time.replace(day=booked_utc_time.day + 1)

        local_tz = get_localzone()

        booked_local_time = booked_utc_time.astimezone(local_tz)
        expired_local_time = booked_local_time.replace(hour=booked_local_time.hour + duration)

        field = {
            "UserID": userId,
            "Url": link,
            "Content": content,
            "Time": time,
            "Duration": duration,
            "StartTime": booked_local_time,
            "CreatedAt": datetime.datetime.now(),
            "ExpiredAt": expired_local_time
        }
        
        res = await insertFields('tbl_ads', field)

        if tokenMode == 0:
            field = "ETH_Amount"
        else:
            field = "BNB_Amount"

        kind = "UserID='{}'".format(userId)
        prevAmount = await readFieldsWhereStr('tbl_users', field, kind)

        curAmount = float(prevAmount[0][0]) - amount

        res = await updateSetFloatWhereStr("tbl_users", field, curAmount, "UserID", userId)
    except:
        print("Create Ads error")
        return res
    return res
