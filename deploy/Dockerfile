FROM python

USER root

WORKDIR /fileserver

RUN python3 -m pip install --upgrade pip \
    && pip install Flask 

COPY source/ .
ENTRYPOINT [ "flask", "--app", "run", "run", "-h", "0.0.0.0" ]