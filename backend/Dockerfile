FROM public.ecr.aws/lambda/python:3.9

# Copy requirements and install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project to /var/task
COPY . .

# Set the command to the mangum handler
CMD [ "backend.main.handler" ]
