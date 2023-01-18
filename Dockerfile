FROM python:3.6-alpine

# To reduce build times when developing/uploading
RUN apk add build-base libffi-dev && pip install binance-connector==1.18.0

WORKDIR /app
COPY . .
# RUN pip install -r requirements.txt

CMD ["python3","-u","/app/run.py"]
