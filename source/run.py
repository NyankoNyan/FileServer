from __future__ import annotations
from datetime import timedelta
from flask import Flask, jsonify, request, send_file, make_response
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, get_jwt
import json
import os
import shutil


class Storage:
    __slots__ = ['name', 'path', 'write_permissions', 'read_permissions']

    def __init__(self, config: dict(str)) -> None:
        self.name = config['name']
        self.path = config['path']
        self.write_permissions = config.get('write_permissions', 'none')
        self.read_permissions = config.get('read_permissions', 'none')

    def check_read(self, groups: list(str)) -> bool:
        if self.read_permissions == 'none':
            return False
        elif self.read_permissions == 'all':
            return True
        else:
            return self.read_permissions in groups

    def check_write(self, groups: list(str)) -> bool:
        if self.write_permissions == 'none':
            return False
        elif self.write_permissions == 'all':
            return True
        else:
            return self.write_permissions in groups


class User:
    __slots__ = ['name', 'auth_method', 'password', 'groups']

    def __init__(self, settings: dict) -> None:
        self.name: str = settings.get('name')
        if self.name is None or len(self.name) == 0:
            raise Exception('Empty user name')
        self.auth_method: str = settings.get('auth_method', 'password')
        self.password = settings.get('password', '')
        self.groups = settings.get('groups', ['Guest'])


config_path = os.getenv('FS_CONFIG', 'config/config.json')
users_path = os.getenv('FS_USERS', 'config/users.json')
with open(config_path) as f:
    config = json.load(f)
storages = {c['name']: Storage(c) for c in config['storages']}

with open(users_path) as f:
    users = {u['name']: User(u) for u in json.load(f)}


app = Flask(__name__)
jwt = JWTManager(app)
app.config["JWT_SECRET_KEY"] = "this-is-secret-key"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)
jwt_blocklist = set()


def add_slash(s):
    if len(s) > 0 and s[0] != '/':
        return '/' + s
    else:
        return s


class RequestError(Exception):
    pass


def get_storage() -> Storage:
    storage_name = request.args.get('s')
    if storage_name is None:
        raise RequestError('Missing storage parameter(s)')

    storage = storages.get(storage_name)
    if storage is None:
        raise RequestError(f'Storage "{storage_name}" not found')

    return storage


def get_filepath(storage: Storage) -> str:
    file = request.args.get('f', '')
    if file is None:
        raise RequestError('Missing file parameter(f)')

    if len(file) > 0 and file[0] != '/':
        file = '/' + file

    fullpath = storage.path + file
    if fullpath != os.path.normpath(fullpath):
        raise RequestError('Unsupported path symbols')

    return fullpath


def get_file_content():
    if len(request.files) == 0:
        raise RequestError('File not found in request')
    file = request.files.get('upload_file')
    if file is None:
        raise RequestError('File not found')
    return file


def get_user_groups() -> list(str):
    user_id = get_jwt_identity()
    user = users.get(user_id)
    if user is None:
        return ["Guest"]
    else:
        return user.groups


@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    return jti in jwt_blocklist


@app.route(config['url_prefix'] + '/<path:url>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@jwt_required(optional=True)
def fs_request(url):
    if url == 'login':
        if request.method != 'GET':
            return jsonify(msg='Bad request method'), 400
        return login()
    elif url == 'logout':
        if request.method != 'GET':
            return jsonify(msg='Bad request method'), 400
        return logout()
    else:
        if request.method == 'GET':
            return get_file_or_file_list(url)
        elif request.method == 'DELETE':
            return delete(url)
        elif request.method in ('POST', 'PUT'):
            return post_put(url)
        else:
            return jsonify(msg='Bad request method'), 400


def login():
    if request.is_json:
        user_name = request.json['user']
    else:
        user_name = request.form['user']

    user = users.get(user_name)
    if user is None:
        print(f'Unknown user {user_name} login failure')
        return jsonify(msg='Login failure'), 400

    if user.auth_method == 'password':
        if request.is_json:
            user_password = request.json['password']
        else:
            user_password = request.form['password']
        if user_password != user.password:
            print(f'Bad password for {user.name}')
            return jsonify(msg='Login failure'), 400
    else:
        print(f'Unknown auth method {user.auth_method} for {user.name}')
        return jsonify(msg='Login failure'), 400

    token = create_access_token(identity=user.name)
    print(f'User {user.name} succesful login')
    return jsonify(msg='Login succesful!', access_token=token), 200


def logout():
    payload = get_jwt()
    if payload is None:
        return jsonify(msg='You are not logining'), 400
    jti = payload.get('jti')
    if jti is None:
        return jsonify(msg='You are not logining'), 400
    if str(jti) in jwt_blocklist:
        return jsonify(msg='You are not logining'), 400
    jwt_blocklist.add(str(jti))
    user_id = get_jwt_identity()
    print(f'User {user_id} succesful logout')
    return jsonify(msg='Logout succesfull'), 200


def get_file_or_file_list(url: str):
    first_slash = url.find('/')
    if first_slash == -1:
        storage_name = url
        path = ''
    else:
        storage_name = url[0:first_slash]
        path = url[first_slash+1:]

    storage = storages.get(storage_name)
    if storage is None:
        return jsonify(msg='Not found'), 404

    groups = get_user_groups()
    if not storage.check_read(groups):
        print(f'Permisisons deny {get_jwt_identity()} {storage.name}')
        return jsonify(msg='Permissions deny'), 400

    if len(path) == 0:
        fullpath = storage.path
    else:
        fullpath = storage.path + '/' + path
    if fullpath != os.path.normpath(fullpath):
        return jsonify(msg='Not found'), 404

    if not os.path.exists(fullpath):
        return jsonify(msg='Not found'), 404

    if os.path.isdir(fullpath):
        result = []
        for content in os.listdir(fullpath):
            subpath = fullpath + '/' + content
            result.append({
                "path": content,
                "is_dir": os.path.isdir(subpath)
            })
        return jsonify(msg='Directory list', files=result), 200
    else:
        return send_file(fullpath, as_attachment=True)


def delete(url: str):
    first_slash = url.find('/')
    if first_slash == -1:
        storage_name = url
        path = ''
    else:
        storage_name = url[0:first_slash]
        path = url[first_slash+1:]

    storage = storages.get(storage_name)
    if storage is None:
        return jsonify(msg='Not found'), 404

    groups = get_user_groups()
    if not storage.check_write(groups):
        print(f'Permisisons deny {get_jwt_identity()} {storage.name}')
        return jsonify(msg='Permissions deny'), 400

    fullpath = storage.path + '/' + path
    if fullpath != os.path.normpath(fullpath):
        return jsonify(msg='Not found'), 404

    if not os.path.exists(fullpath):
        return jsonify(msg='Not found'), 404

    if os.path.isdir(fullpath):
        shutil.rmtree(fullpath)
        return jsonify(msg='Directory removed'), 200
    else:
        os.remove(fullpath)
        return jsonify(msg='File removed'), 200


def post_put(url: str):
    first_slash = url.find('/')
    if first_slash == -1:
        storage_name = url
        path = ''
    else:
        storage_name = url[0:first_slash]
        path = url[first_slash+1:]

    storage = storages.get(storage_name)
    if storage is None:
        return jsonify(msg='Not found'), 404

    groups = get_user_groups()
    if not storage.check_write(groups):
        print(f'Permisisons deny {get_jwt_identity()} {storage.name}')
        return jsonify(msg='Permissions deny'), 400

    fullpath = storage.path + '/' + path
    if fullpath != os.path.normpath(fullpath):
        return jsonify(msg='Not found'), 404

    if len(request.files) == 0:
        if os.path.exists(fullpath):
            if request.method == 'POST':
                return jsonify(msg='Already exists'), 400
            elif os.path.isdir(fullpath):
                return jsonify(msg='Already exists'), 200
            else:
                os.remove(fullpath)
                os.mkdir(fullpath)
                return jsonify(msg='Created'), 200
        else:
            os.mkdir(fullpath)
            return jsonify(msg='Created'), 200
    else:
        if os.path.exists(fullpath):
            if request.method == 'POST':
                return jsonify(msg='Already exists'), 400
            else:
                if os.path.isdir(fullpath):
                    shutil.rmtree(fullpath)
                else:
                    os.remove(fullpath)
        file = get_file_content()
        file.save(fullpath)
        response = make_response(jsonify(msg='Created'))
        response.headers.add('Location', storage.name + '/' + path)
        response.status_code = 200
        return response


if __name__ == '__main__':
    if config.get('secure', False):
        ssl_context = (config.get('public_key'), config.get('private_key'))
    else:
        ssl_context = None
    app.run(host=config.get('host', '127.0.0.1'), ssl_context=ssl_context)
