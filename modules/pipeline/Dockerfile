FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies required for psycopg2 (libpq)
RUN dnf install -y gcc postgresql-devel && \
    dnf clean all

# Copy requirements from the pipeline folder and install
COPY pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire src directory contents to the Lambda task root
COPY pipeline/src/ ${LAMBDA_TASK_ROOT}

# The handler points to app.lambda_handler (since app.py is now at the root of the task path)
CMD ["app.lambda_handler"]
