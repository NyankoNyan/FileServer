import requests


def run_all_tests():
    create_folder()
    upload_file_to_folder()
    get_file_list()
    download_file()
    check_downloaded_file()
    remove_file()
    check_file_exists()
    remove_folder()
    check_folder_exists()


def create_folder():
    r = requests.post('http://localhost:5000/fs/mkdir?s=test&f=test_folder')
    if r.status_code != 200:
        print("create_folder: " + str(r))



def upload_file_to_folder():
    pass


def get_file_list():
    pass


def download_file():
    pass


def check_downloaded_file():
    pass


def remove_file():
    pass


def check_file_exists():
    pass


def remove_folder():
    pass


def check_folder_exists():
    pass


if __name__ == '__main__':
    run_all_tests()
