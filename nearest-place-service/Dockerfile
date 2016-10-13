FROM python:3-alpine
MAINTAINER Tom Bech "tom.bech@sesam.io"
COPY ./service /service
WORKDIR /service
RUN pip install -r requirements.txt
EXPOSE 5001/tcp
ENTRYPOINT ["python"]
CMD ["transform-service.py", "/service/places.json"]
