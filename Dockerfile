FROM python:3.9-slim

# Establish the container working directory
WORKDIR app/
# Copy over the requirements file
COPY requirements.txt .
# Run the pip command to install the requirements
RUN pip install --no-cache-dir -r requirements.txt 

# Copy the service package into the working directory
COPY service/ ./service/

# Create a non-user, change the ownership of app/ and switch to new user
RUN useradd --uid 1000 theia && chown -R theia /app
USER theia

# Expose port 8080 and start server
EXPOSE 8080
CMD ["gunicorn", "--bind=0.0.0.0:8080", "--log-level=info", "service:app"]