from __future__ import annotations
from flask import Flask, jsonify, request, send_file
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
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


@app.route(config['url_prefix'] + '/login', methods=['GET'])
def fs_login():
    if request.is_json:
        user_name = request.json['user']
    else:
        user_name = request.form['user']

    user = users.get(user_name)
    if user is None:
        print(f'Unknown user {user_name} login failure')
        return 'Login failure', 400

    if user.auth_method == 'password':
        if request.is_json:
            user_password = request.json['password']
        else:
            user_password = request.form['password']
        if user_password != user.password:
            print(f'Bad password for {user.name}')
            return 'Login faulure', 400
    else:
        print(f'Unknown auth method {user.auth_method} for {user.name}')
        return 'Login faulure', 400

    token = create_access_token(identity=user.name)
    print(f'User {user.name} succesful login')
    return jsonify(message='Login succesful!', access_token=token)


@app.route(config['url_prefix'] + '/list', methods=['GET'])
@jwt_required(optional=True)
def fs_list():
    try:
        storage = get_storage()
        folder = get_filepath(storage)
    except RequestError as e:
        return e.args[0], 400

    groups = get_user_groups()
    if not storage.check_read(groups):
        print(f'Permisisons deny {get_jwt_identity()} {storage.name}')
        return 'Permissions deny', 400

    if not os.path.isdir(folder):
        print(f"Missing storage directory {folder}")
        return 'Internal server error', 400

    result = []
    for content in os.listdir(folder):
        fullpath = folder + '/' + content
        result.append({
            "path": content,
            "isDir": os.path.isdir(fullpath)
        })

    return jsonify(result)


@app.route(config['url_prefix'] + '/read', methods=['GET'])
@jwt_required(optional=True)
def fs_read():
    try:
        storage = get_storage()
        fullpath = get_filepath(storage)
    except RequestError as e:
        return e.args[0], 400

    groups = get_user_groups()
    if not storage.check_read(groups):
        print(f'Permisisons deny {get_jwt_identity()} {storage.name}')
        return 'Permissions deny', 400

    if not os.path.exists(fullpath):
        return 'File not found '+fullpath, 400

    return send_file(fullpath, as_attachment=True)


@app.route(config['url_prefix'] + '/mkdir', methods=['POST'])
@jwt_required(optional=True)
def fs_mkdir():
    try:
        storage = get_storage()
        fullpath = get_filepath(storage)
    except RequestError as e:
        return e.args[0], 400

    groups = get_user_groups()
    if not storage.check_write(groups):
        print(f'Permisisons deny {get_jwt_identity()} {storage.name}')
        return 'Permissions deny', 400

    if os.path.exists(fullpath):
        return "Directory already exists", 400

    os.mkdir(fullpath)

    return "Created", 200


@app.route(config['url_prefix'] + '/write', methods=['POST'])
@jwt_required(optional=True)
def fs_write():
    try:
        storage = get_storage()
        fullpath = get_filepath(storage)
        file = get_file_content()
    except RequestError as e:
        return e.args[0], 400

    groups = get_user_groups()
    if not storage.check_write(groups):
        print(f'Permisisons deny {get_jwt_identity()} {storage.name}')
        return 'Permissions deny', 400

    file.save(fullpath)

    return "Saved", 200


@app.route(config['url_prefix'] + '/del', methods=['DELETE'])
@jwt_required(optional=True)
def fs_del():
    try:
        storage = get_storage()
        fullpath = get_filepath(storage)
    except RequestError as e:
        return e.args[0], 400

    groups = get_user_groups()
    if not storage.check_write(groups):
        print(f'Permisisons deny {get_jwt_identity()} {storage.name}')
        return 'Permissions deny', 400

    if not os.path.exists(fullpath):
        return 'Path not exists', 400

    if os.path.isdir(fullpath):
        shutil.rmtree(fullpath)
        return 'Directory removed', 200
    else:
        os.remove(fullpath)
        return 'File removed', 200


if __name__ == '__main__':
    if config.get('secure', False):
        ssl_context = (config.get('public_key'), config.get('private_key'))
    else:
        ssl_context = None
    app.run(host=config.get('host', '127.0.0.1'), ssl_context=ssl_context)
