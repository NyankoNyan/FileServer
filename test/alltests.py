import requests
import json

access_token = ''


def run_all_tests():
    request_token()
    create_folder()
    upload_file_to_folder()
    get_file_list()
    download_file()
    remove_file()
    check_file_exists()
    remove_folder()
    check_folder_exists()


def request_token():
    r = requests.get('http://localhost:5000/fs/login',
                     data={'user': 'admin', 'password': 'admin'})
    if r.status_code != 200:
        print(f'request_token: {r.status_code}: {r.text}')
        return
    global access_token
    access_token = json.loads(r.text)['access_token']


def create_folder():
    r = requests.post('http://localhost:5000/fs/mkdir?s=test&f=test_folder',
                      headers={'Authorization': 'Bearer '+access_token})
    if r.status_code != 200:
        print(f'create_folder: {r.status_code}: {r.text}')


def upload_file_to_folder():
    r = requests.post('http://localhost:5000/fs/write?s=test&f=test_folder%2ftest_file.txt',
                      headers={'Authorization': 'Bearer '+access_token},
                      files={'upload_file': open('test_file.txt', 'rb')}
                      )
    if r.status_code != 200:
        print(f'upload_file_to_folder: {r.status_code}: {r.text}')


def get_file_list():
    r = requests.get('http://localhost:5000/fs/list?s=test&f=test_folder',
                     headers={'Authorization': 'Bearer '+access_token})
    if r.status_code != 200:
        print(f'get_file_list: {r.status_code}: {r.text}')
        return
    files = json.loads(r.text)
    if len(files) != 1:
        print(f'get_file_list: Files count {len(files)}')
        return
    if files[0]['path'] != 'test_file.txt' or files[0]['isDir'] != False:
        print(f'get_file_list: File content {files[0]}')


def download_file():
    r = requests.get(
        'http://localhost:5000/fs/read?s=test&f=test_folder%2ftest_file.txt',
        headers={'Authorization': 'Bearer '+access_token})
    if r.status_code != 200:
        print(f'download_file: {r.status_code}: {r.text}')
        return
    with open('test_file.txt', 'r') as f:
        local_content = f.read()
    if local_content != r.text:
        print(f'download_file: Downloaded content not equals original')
        print(local_content)
        print(r.text)


def remove_file():
    r = requests.delete(
        'http://localhost:5000/fs/del?s=test&f=test_folder%2ftest_file.txt',
        headers={'Authorization': 'Bearer '+access_token})
    if r.status_code != 200:
        print(f'remove_file: {r.status_code}: {r.text}')


def check_file_exists():
    r = requests.get('http://localhost:5000/fs/list?s=test&f=test_folder',
                     headers={'Authorization': 'Bearer '+access_token})
    if r.status_code != 200:
        print(f'check_file_exists: {r.status_code}: {r.text}')
        return
    files = json.loads(r.text)
    if len(files) != 0:
        print('check_file_exists: Folder is not empty')


def remove_folder():
    r = requests.delete(
        'http://localhost:5000/fs/del?s=test&f=test_folder',
        headers={'Authorization': 'Bearer '+access_token})
    if r.status_code != 200:
        print(f'remove_folder: {r.status_code}: {r.text}')


def check_folder_exists():
    r = requests.get('http://localhost:5000/fs/list?s=test&f=',
                     headers={'Authorization': 'Bearer '+access_token})
    if r.status_code != 200:
        print(f'check_folder_exists: {r.status_code}: {r.text}')
        return
    files = json.loads(r.text)
    if len(files) != 0:
        print('check_file_exists: Folder is not empty')


if __name__ == '__main__':
    run_all_tests()
