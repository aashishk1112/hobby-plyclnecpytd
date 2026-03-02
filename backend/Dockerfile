FROM public.ecr.aws/lambda/python:3.9

# Install build dependencies if needed (e.g., for certain python packages)
# RUN yum install -y gcc-c++ 

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code to standard Lambda location
COPY . /var/task

# Set the command to the mangum handler
CMD [ "main.handler" ]
