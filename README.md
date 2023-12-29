Это файлопомойка. Я не очень умный, поэтому запускаю её так.
```
source .venv/bin/activate
cd source
run python3 -m run
```

Вы можете использовать Docker.
Для этого надо создать образ, запустив скрипт
```
./docker-build.sh
```

Также можно развернуть обвязку для docker-compose через запуск скрипта
```
./deploy_docker_app.sh -t=$TARGET_FOLDER -p=$REPO_FOLDER
```

Список примеров, как правильно использовать местный REST можно посмотреть в файле
```
test/alltests.py
```

