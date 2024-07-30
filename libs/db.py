import mysql.connector
import datetime

db = mysql.connector.connect(host = "bbt-mysql-bluebigthink.e.aivencloud.com", user = "avnadmin", passwd = "AVNS_Uio0Wd1KKJsWVMVn9G2", port=22945, database = "DB_AleekkCasino")
cur = db.cursor()


async def updateSetStrWhereStr(table: str, field: str, value: str, where: str, wherestr: str) -> bool:
    bRes = False
    try:
        query = f"UPDATE {table} SET {field}='{value}' WHERE {where}='{wherestr}';"
        print(query)
        cur.execute(query)
        db.commit()
        bRes = True
        print("Field updated sucessfully")
    except:
        bRes = False
        print("update error")
    return bRes


async def updateSetFloatWhereStr(table: str, field: str, value: float, where: str, wherestr: str) -> bool:
    bRes = False
    try:
        query = f"UPDATE {table} SET {field}={value} WHERE {where}='{wherestr}';"
        print(query)
        cur.execute(query)
        db.commit()
        bRes = True
        print("Field updated sucessfully")
    except:
        bRes = False
        print("update error")
    return bRes


async def getTopFieldsByLimit(table: str, field: str, orderColumn: str, limit: str) -> bool:
    res = []
    try:
        query = f"SELECT {field} FROM {table} ORDER BY {orderColumn} DESC LIMIT {limit};"
        
        print(query)
        cur.execute(query)
        res = cur.fetchall()
    except:
        print("Get Top Values error")
    return res


async def readFieldsWhereStr(table: str, field: str, kind: str) -> any:
    res = []
    try:
        query = f"SELECT {field} FROM {table} WHERE {kind};"
        print(query)
        cur.execute(query)
        res = cur.fetchall()
    except:
        print("Read Field error: field:{}, kind:{}".format(field, kind))
    return res


async def insertFields(table: str, field: dict) -> bool:
    bRes = False
    try:
        placeholders = ', '.join(['%s'] * len(field))
        columns = ', '.join(field.keys())

        query = "INSERT INTO %s ( %s ) VALUES ( %s )" % (table, columns, placeholders)
        print(query)

        cur.execute(query, list(field.values()))
        db.commit()

        bRes = True
        print("Field created sucessfully")
    except:
        print("Insert error")
    return bRes


async def insertInitialCoinInfos() -> bool:
    bRes = False
    try:
        query = "INSERT INTO tbl_cryptos (Symbol, CoinId) VALUES (\"eth\", \"ethereum\")"

        cur.execute(query)
        db.commit()

        query = "INSERT INTO tbl_cryptos (Symbol, CoinId) VALUES (\"bnb\", \"binancecoin\")"

        cur.execute(query)
        db.commit()

        bRes = True
        print("Initial Coin Infos created sucessfully")
    except:
        print("Initial Coin Infos error")
    return bRes
