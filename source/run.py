from flask import Flask, jsonify, request, send_file
import json
import os


class Storage:
    __slots__ = ['name', 'path']

    def __init__(self, name, path) -> None:
        self.name = name
        self.path = path


config_path = os.getenv('FS_CONFIG', 'config.json')
with open(config_path) as f:
    config = json.load(f)
storages = {c['name']: Storage(c['name'], c['path'])
            for c in config['storages']}


app = Flask(__name__)


@app.route(config['url_prefix'] + '/list', methods=['GET'])
def fs_list():
    storage_name = request.args.get('s')

    if storage_name is None:
        return 'Missing storage parameter(s)', 400

    subpath = request.args.get('f', '')

    if len(subpath) > 0 and subpath[0] != '/':
        subpath = '/' + subpath

    storage = storages.get(storage_name)
    if storage is None:
        return f'Storage "{storage_name}" not found', 400

    folder = storage.path + subpath
    if folder != os.path.normpath(folder):
        return 'Unsupported path symbols', 400

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
def fs_read():
    storage_name = request.args.get('s')
    if storage_name is None:
        return 'Missing storage parameter(s)', 400

    storage = storages.get(storage_name)
    if storage is None:
        return f'Storage "{storage_name}" not found', 400

    file_name = request.args.get('f')
    if file_name is None:
        return 'Missing file parameter(f)', 400

    if file_name[0] != '/':
        file_name = '/' + file_name

    fullpath = storage.path + file_name
    if fullpath != os.path.normpath(fullpath):
        return 'Unsupported path symbols', 400

    if not os.path.exists(fullpath):
        return 'File not found '+fullpath, 400

    return send_file(fullpath, as_attachment=True)
