FROM python:3.11

# Prepare the application
WORKDIR /app
COPY . /app
RUN pip install -e .

CMD ["python", "-m", "fal_bot"]
