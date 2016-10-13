FROM python:3-alpine
MAINTAINER Tom Bech "tom.bech@sesam.io"
COPY ./service /service
WORKDIR /service
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["ais-service", "-h"]
