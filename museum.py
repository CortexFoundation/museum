import pymongo
from flask import Flask, request, jsonify
from web3 import Web3
from web3.middleware import geth_poa_middleware
from flask_cors import *
from os import path, rename
import json
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import requests
import validators


# 连接数据库
client = pymongo.MongoClient('127.0.0.1', 27017)
db = client.museum
# 记录展馆信息
hall = db.hall
# 记录作品信息
works = db.works
# 记录个人信息
user = db.user
# 记录订阅的邮箱
email = db.email

w3 = Web3(Web3.HTTPProvider(''))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)
folder = 'works'
app = Flask(__name__, static_url_path='/data', static_folder=folder)
CORS(app, supports_credentials=True)

dir_path = path.dirname(path.realpath(__file__))
with open(str(path.join(dir_path, 'contract_abi.json')),
          'r') as abi_definition:
    abi = json.load(abi_definition)
contract_address = ''
contract = w3.eth.contract(address=contract_address, abi=abi)
host = 'http://223.94.61.114:38899/data/'
uri = 'http://223.94.61.114:38899/'
official_address = '0x9Edb74ccf3AEe5c02063247fB13149a3B12ED961'


# 根据字符串获取hash
def get_hash(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post('http://127.0.0.1:5001/api/v0/add', files=files)
        data = json.loads(response.text)
        hash_code = data['Hash']
    return hash_code


# 获取用户信息
def get_info(address):
    params = {
        'address': address
    }
    data = requests.get(uri + 'get_user_info', params = params).text
    data = json.loads(data)
    return data


# 创建展馆
@app.route('/create_hall', methods=['POST'])
def create_hall():
    user_ad = request.form.get('address')
    user_ad = w3.toChecksumAddress(user_ad)
    hall_name = request.form.get('name')
    hall_type = request.form.get('type')
    hall_description = request.form.get('description')
    hall_image = request.files['image']
    image_name = hall_image.filename
    image_name = secure_filename(image_name)
    img_type = image_name.rsplit('.')[-1].lower()
    old_path = folder + '/hall_image/' + image_name
    hall_image.save(old_path)
    img_hash = get_hash(old_path)
    new_path = folder + '/hall_image/' + img_hash + '.' + img_type
    rename(old_path, new_path)
    official = False
    if user_ad == official_address:
        official = True
    _id = hall.insert_one({
        'user_address': user_ad,
        'hall_name': hall_name,
        'hall_type': hall_type,
        'hall_description': hall_description,
        'works_token': [],
        'hall_image': new_path[6:],
        'official': official
    })
    return str(_id.inserted_id)


# 获取展馆列表
@app.route('/get_user_hall', methods=['GET'])
def get_user_hall():
    limit = 4
    user_ad = request.args.get('address')
    page = request.args.get('page')
    official = request.args.get('official')
    hot = request.args.get('hot')
    if user_ad:
        user_ad = w3.toChecksumAddress(user_ad)
        cursor_dict = {'user_address': user_ad}
    else:
        cursor_dict = {}
    if official:
        if official == 'true':
            cursor_dict['official'] = True
        elif official == 'false':
            cursor_dict['official'] = False
        else:
            return 'args official error', 400
    user_hall = hall.find(cursor_dict)
    if hot:
        if hot == 'true':
            user_hall = user_hall.sort([('access_num', -1)])
    hall_arr = []
    if page:
        page = int(page)
        data_count = hall.count_documents(cursor_dict)
        if data_count % limit ==0:
            total_page = int(data_count / limit)
        else:
            total_page = int(data_count / limit) + 1
        start = (page - 1) * limit
        if page == total_page:
            end = data_count
        else:
            end = start + limit
        index = 0
        for s_hall in user_hall:
            if not index < end:
                break
            if not index < start:
                user_address = s_hall['user_address']
                official = False
                if user_address == official_address:
                    official = True
                data = get_info(user_address)
                hall_arr.append({
                    'hall_id': str(s_hall['_id']),
                    'hall_name': s_hall['hall_name'],
                    'hall_type': s_hall['hall_type'],
                    'hall_description': s_hall['hall_description'],
                    'user_address': user_address,
                    'works_token': s_hall['works_token'],
                    'hall_image': host + s_hall['hall_image'],
                    'owner_name': data['name'],
                    'owner_avatar': data['avatar'],
                    'official': official
                })
            index = index + 1
    else:
        for s_hall in user_hall:
            user_address = s_hall['user_address']
            official = False
            if user_address == official_address:
                official = True
            data = get_info(user_address)
            hall_arr.append({
                'hall_id': str(s_hall['_id']),
                'hall_name': s_hall['hall_name'],
                'hall_type': s_hall['hall_type'],
                'hall_description': s_hall['hall_description'],
                'user_address': s_hall['user_address'],
                'works_token': s_hall['works_token'],
                'hall_image': host + s_hall['hall_image'],
                'owner_name': data['name'],
                'owner_avatar': data['avatar'],
                'official': official
            })
    return jsonify(hall_arr)


# 获取拥有的作品id
@app.route('/get_owned_works', methods=['GET'])
def get_owned_works():
    user_ad = request.args.get('address')
    user_ad = w3.toChecksumAddress(user_ad)
    res_arr = []
    works_doc = works.find({'owner': user_ad})
    for doc in works_doc:
        creator = doc['creator']
        creator_name = get_info(creator)['name']
        owner= doc['owner']
        owner_name = get_info(owner)['name']
        res_arr.append({
            'token_id': doc['token_id'],
            'data': host + doc['art_path'],
            'name': doc['name'],
            'type': doc['type'],
            'contract': doc['contract'],
            'description': doc['description'],
            'creator': creator,
            'creator_name': creator_name,
            'owner': owner,
            'owner_name': owner_name
        })
    return jsonify(res_arr)


# 添加作品到展馆
@app.route('/add_works', methods=['POST'])
def add_works():
    user_ad = request.form.get('address')
    user_ad = w3.toChecksumAddress(user_ad)
    hall_id = request.form.get('id')
    hall_id = ObjectId(hall_id)
    token_arr = request.form.get('token_arr')
    token_arr = json.loads(token_arr)
    doc = hall.find_one({'_id': hall_id})
    works_token = doc['works_token']
    for token_id in token_arr:
        #works_doc = works.find_one({'token_id': token_id})
        works_token.append(token_id)
    if not len(works_token) == 0:
        works_token = list(set(works_token))
        works_token.sort()
    try:
        hall.update_one({'_id': hall_id}, {'$set': {'works_token': works_token}})
    except Exception as e:
        app.logger.exception(e)
        return 'add failed', 500
    return 'add success'


# 获取展馆具体信息
@app.route('/get_hall', methods=['GET'])
def get_hall():
    hall_id = request.args.get('id')
    hall_id = ObjectId(hall_id)
    hall_num = hall.count_documents({'_id': hall_id})
    if hall_num == 0:
        return 'museum does not exist', 400
    doc = hall.find_one({'_id': hall_id})
    try:
        access_num = doc['access_num']
    except KeyError:
        access_num = 0
    except Exception as e:
        app.logger.exception(e)
        return {}
    hall.update_one({'_id': hall_id},{'$set':{'access_num': access_num + 1}})
    works_token = doc['works_token']
    official = False
    if doc['user_address'] == official_address:
        official = True
    res_arr = [{
        '_id': str(hall_id),
        'user_address': doc['user_address'],
        'hall_name': doc['hall_name'],
        'hall_type': doc['hall_type'],
        'hall_description': doc['hall_description'],
        'works_token': works_token,
        'hall_image': host + doc['hall_image'],
        'official': official
    }]
    for token_id in works_token:
        works_doc = works.find_one({'token_id': token_id})
        owner = works_doc['owner']
        user_count = user.count_documents({'_id': owner})
        if user_count == 0:
            owner_name = ''
            owner_avatar = host + 'avatar/default.png'
        else:
            user_doc = user.find_one({'_id': owner})
            owner_name = user_doc['name']
            if user_doc['avatar']:
                owner_avatar = host + user_doc['avatar']
            else:
                owner_avatar = ''
        res_arr.append({
            'name': works_doc['name'],
            'token_id': token_id,
            'description': works_doc['description'],
            'owner': owner,
            'owner_name': owner_name,
            'owner_avatar': owner_avatar,
            'creator': works_doc['creator'],
            'data': host + works_doc['art_path']
        })
    return jsonify(res_arr)


# 获取作品
@app.route('/get_works', methods=['GET'])
def get_works():
    token_id = request.args.get('token_id')
    token_id = int(token_id)
    doc = works.find_one({'token_id': token_id})
    owner = doc['owner']
    owner_data = get_info(owner)
    creator = doc['creator']
    creator_data = get_info(creator)
    result = {
        'token_id': token_id,
        'data': host + doc['art_path'],
        'name': doc['name'],
        'type': doc['type'],
        'contract': doc['contract'],
        'description': doc['description'],
        'creator': creator,
        'owner': owner,
        'owner_name': owner_data['name'],
        'creator_name': creator_data['name']
    }
    return result


# 更新用户信息
@app.route('/update_user_info', methods=['POST'])
def update_user_info():
    name = request.form.get('name')
    description = request.form.get('description')
    facebook = request.form.get('facebook')
    twitter = request.form.get('twitter')
    pinterest = request.form.get('pinterest')
    instagram = request.form.get('instagram')
    homepage = request.form.get('homepage')
    user_address = request.form.get('address')
    user_address = w3.toChecksumAddress(user_address)
    user_count = user.count_documents({'_id': user_address})
    avatar = request.form.get('avatar')
    default_avatar = 'avatar/default.png'
    flag = False
    if avatar == None:
        flag = True
        avatar = request.files['avatar']
        avatar_name = avatar.filename
        avatar_type = avatar_name.rsplit('.')[-1].lower()
        avatar_path = folder + '/avatar/' + user_address + '.' + avatar_type
        avatar.save(avatar_path)
        default_avatar = avatar_path[6:]
    if user_count == 0:
        try:
            user.insert_one({
                '_id': user_address,
                'name': name,
                'description': description,
                'facebook': facebook,
                'twitter': twitter,
                'pinterest': pinterest,
                'instagram': instagram,
                'homepage': homepage,
                'avatar': default_avatar,
                'follower': [],
                'following': []
            })
        except Exception as e:
            app.logger.exception(e)
            return 'update failed', 500
    else:
        try:
            user.update_one(
                {'_id': user_address},
                {
                    '$set': {
                        'name': name,
                        'description': description,
                        'facebook': facebook,
                        'twitter': twitter,
                        'pinterest': pinterest,
                        'instagram': instagram,
                        'homepage': homepage,
                        'follower': [],
                        'following': []
                    }
                }
            )
            if flag:
                user.update_one({'_id': user_address},{'$set':{'avatar': avatar_path[6:]}})
        except Exception as e:
            app.logger.exception(e)
            return 'update failed', 500
    return 'update success'


# 获取用户信息
@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    user_address = request.args.get('address')
    user_address = w3.toChecksumAddress(user_address)
    user_count = user.count_documents({'_id': user_address})
    avatar = 'avatar/default.png'
    if not user_count:
        user.insert_one({
            '_id': user_address,
            'name': '',
            'description': '',
            'facebook': '',
            'twitter': '',
            'pinterest': '',
            'instagram': '',
            'homepage': '',
            'avatar': avatar,
            'follower': [],
            'following': []
        })
    doc = user.find_one({'_id': user_address})
    doc['user_address'] = doc['_id']
    del doc['_id']
    doc['avatar'] = host + doc['avatar']
    return doc


# 获取关注和粉丝列表
@app.route('/get_follow', methods=['GET'])
def get_follow():
    user_address = request.args.get('address')
    user_address = w3.toChecksumAddress(user_address)
    json_dict = {
        'count_follower': 0,
        'count_following': 0,
        'follower': [],
        'following': []
    }
    try:
        user_doc = user.find_one({'_id': user_address})
        count_follower = len(user_doc['follower'])
        count_following = len(user_doc['following'])
        follower = []
        for follower_ad in user_doc['follower']:
            follower_data = get_info(follower_ad)
            follower.append({
                'address': follower_ad,
                'name': follower_data['name'],
                'avatar': follower_data['avatar']
            })
        following = []
        for following_ad in user_doc['following']:
            following_data = get_info(following_ad)
            following.append({
                'address': following_ad,
                'name': following_data['name'],
                'avatar': following_data['avatar']
            })
        json_dict['count_follower'] = count_follower
        json_dict['count_following'] = count_following
        json_dict['follower'] = follower
        json_dict['following'] = following
        return json_dict
    except Exception as e:
        app.logger.exception(e)
        return json_dict


# 更改关注状态
@app.route('/change_follow', methods=['POST'])
def change_follow():
    ad_from = request.form.get('address_from')
    ad_from = w3.toChecksumAddress(ad_from)
    ad_to = request.form.get('address_to')
    ad_to = w3.toChecksumAddress(ad_to)
    status = request.form.get('type')
    try:
        get_info(ad_from)
        get_info(ad_to)
    except Exception as e:
        app.logger.exception(e)
    # 添加关注
    if status == '1':
        try:
            user.update_one({'_id': ad_from},{'$addToSet':{'following':ad_to}})
            user.update_one({'_id': ad_to},{'$addToSet':{'follower':ad_from}})
            return 'add success'
        except Exception as e:
            app.logger.exception(e)
            return 'add false', 500
    # 取消关注
    if status == '2':
        try:
            user.update_one({'_id': ad_from},{'$pull':{'following':ad_to}})
            user.update_one({'_id': ad_to},{'$pull':{'follower':ad_from}})
            return 'cancel success'
        except Exception as e:
            app.logger.exception(e)
            return 'cancel false', 500


# 获取邮箱
@app.route('/subscribe_status', methods=['POST'])
def subscribe_status():
    email_address = request.form.get('email')
    if not validators.email(email_address):
        return 'email error', 400
    try:
        email.update_one({'_id': 1}, {'$addToSet':{'email':email_address}})
        return 'subscribe success'
    except Exception as e:
        app.logger.exception(e)
        return 'subscribe failed', 500
