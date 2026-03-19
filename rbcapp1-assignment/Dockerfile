FROM python:3.11-slim

RUN pip install flask elasticsearch==8.13.0

WORKDIR /app

COPY test1/ /app/test1/

EXPOSE 5000

CMD ["python3", "/app/test1/app.py"]
