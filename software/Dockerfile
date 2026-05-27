FROM python:3.14-slim

WORKDIR /software

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8111
EXPOSE 8111

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8111"]
