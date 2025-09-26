# This Dockerfile builds a container image for your FastAPI e-commerce assistant app.
# Uses the official Python 3.11.9 image as the base.
# Sets the working directory inside the container to /app.
# Copies dependency files to the container.
# Copies your main application code (prod_assistant folder) into the container.
# Installs Python dependencies listed in requirements.txt.
# Copies all remaining files (including templates, static assets, etc.) into the container.
# Tells Docker that the container will listen on port 8000.
# Runs the FastAPI app using Uvicorn, making it accessible on all network interfaces at port 8000.


FROM python:3.11.9

WORKDIR /app

COPY requirements.txt pyproject.toml ./

COPY prod_assistant ./prod_assistant

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "prod_assistant.router.main:app", "--host", "0.0.0.0", "--port", "8000"]