FROM python:3.10-slim-buster

WORKDIR /opt
COPY ../Pipfile /opt/
COPY ../Pipfile.lock /opt/
RUN pip3 install --upgrade pipenv && \
    pipenv install --system && \
    pip3 uninstall pipenv -y

COPY ../tasks /opt/

CMD ["uvicorn", "--host", "0.0.0.0", "main:app"]
