FROM python

USER root

WORKDIR /fileserver

RUN python3 -m pip install --upgrade pip \
    && pip install Flask \
    && pip install flask_jwt_extended

COPY source/ .
ENTRYPOINT [ "python3", "-m", "run" ]