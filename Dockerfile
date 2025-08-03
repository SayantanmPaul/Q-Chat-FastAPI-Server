FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy application code
COPY . .

# expose port
EXPOSE 8000

# run application command
CMD [ "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000" ]