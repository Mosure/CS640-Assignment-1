FROM hctimitch/switchyard:latest

WORKDIR /app

COPY . /app

RUN chmod +x run_tests.sh

CMD ./run_tests.sh
