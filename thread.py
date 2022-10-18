from web3 import Web3
import json
from web3.middleware import geth_poa_middleware
import flask
from flask_cors import CORS
import os
import time
import pymongo
import requests
from datetime import datetime
from threading import Thread


client = pymongo.MongoClient('127.0.0.1', 27017)
db = client.museum
block = db.block
works = db.works
email = db.email


w3 = Web3(Web3.HTTPProvider('http://storage.cortexlabs.ai:30089'))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)
folder = 'works'
server = flask.Flask(__name__, static_url_path='/data', static_folder=folder)
CORS(server, supports_credetials=True)
# 与合约交互
dir_path = os.path.dirname(os.path.realpath(__file__))
with open(str(os.path.join(dir_path, 'contract_abi.json')),
          'r') as abi_definition:
    abi = json.load(abi_definition)
address = '0x5A12356240d0cba1a201161D4c81Afb556a7FD4A'
contract = w3.eth.contract(address=address, abi=abi)
ipfs_url = 'http://127.0.0.1:8080/ipfs/'
mint_str = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
if not os.path.exists(folder):
    os.mkdir(folder)
if not os.path.exists(folder + '/hall_image'):
    os.mkdir(folder + '/hall_image')
if not os.path.exists(folder + '/avatar'):
    os.mkdir(folder + '/avatar')
try:
    email.insert_one({'_id': 1})
except Exception:
    pass


def stamp_to_str(time_stamp):
    time_temp = float(time_stamp)
    time_str = datetime.utcfromtimestamp(time_temp).strftime('%Y-%m-%d %H:%M:%S.%f')
    return time_str


def handle(event_list):
    for event in event_list:
        topics = event['topics']
        if topics[0].hex() == mint_str:
            ad_to = '0x' + topics[2].hex()[26:]
            ad_to = w3.toChecksumAddress(ad_to)
            token_id = int(topics[3].hex(), 16)
            block_num = event['blockNumber']
            block_data = w3.eth.get_block(block_num)
            time_stamp = block_data['timestamp']
            if int(topics[1].hex()[2:], 16) == 0:
                if not os.path.exists(folder + '/' +ad_to):
                    os.mkdir(folder + '/' +  ad_to)
                m_gas = contract.functions.tokenURI(token_id).estimateGas()
                metadata_hash = contract.functions.tokenURI(token_id).call({'gas': m_gas})
                metadata_url = ipfs_url + metadata_hash
                text = requests.get(metadata_url).text
                metadata = json.loads(text)
                name = metadata['name']['value']
                description = metadata['description']['value']
                author = metadata['author']['value']
                art_hash = metadata['fileSource']['value']
                art_type = metadata['fileExtension']['value']
                art = requests.get(ipfs_url + art_hash).content
                art_name = '{}_{}.{}'.format(str(token_id), art_hash, art_type)
                art_path = '{}/{}/{}'.format(folder, ad_to, art_name)
                with open(art_path, 'wb') as fp:
                    fp.write(art)
                works_dict = {
                    'token_id': token_id,
                    'art_path': art_path[6:],
                    'creator': ad_to,
                    'owner': ad_to,
                    'description': description,
                    'name': name,
                    'type': art_type,
                    'contract': address,
                    'create_time': stamp_to_str(time_stamp)
                }
                works.insert_one(works_dict)
            else:
                works.update_one(
                    {'token_id': token_id},
                    {'$set': {
                        'owner': ad_to
                    }})


# 事件循环
def log_loop():
    while 1:
        try:
            while 1:
                doc = block.find_one({'_id':1})
                fromBlock = doc['block']
                toBlock = w3.eth.block_number
                try:
                    event_list = w3.eth.getLogs({'address': address, 'fromBlock': fromBlock,'toBlock':toBlock})
                    if not len(event_list) == 0:
                        handle(event_list)
                except Exception as e:
                    pass
                fromBlock = toBlock+1
                block.update_one({'_id':1},{'$set':{'block':fromBlock}})
                time.sleep(15)
        except Exception as e:
            pass
        time.sleep(15)


log_loop()
t1 = Thread(target=log_loop)
t1.start()
# event_list = w3.eth.getLogs({'address': address, 'fromBlock': 6650656,'toBlock':6650712})
# if not len(event_list) == 0:
#     handle(event_list)

