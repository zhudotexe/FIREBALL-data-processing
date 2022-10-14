# syntax=docker/dockerfile:1
# Dockerfile to run the explorer server. Requires heuristics to be computed already.
# Mount the input and output directories when running:
# $ docker build . -t explorer_server
# $ docker run -p 31415:31415 -v $(pwd)/data:/app/data -v $(pwd)/heuristic_results:/app/heuristic_results explorer_server

FROM nikolaik/python-nodejs:python3.10-nodejs18

# setup explorer frontend deps
WORKDIR /app/explorer
COPY explorer/package*.json ./
RUN npm install

# setup explorer backend deps
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Bundle app source
COPY . .

# build frontend
WORKDIR /app/explorer
RUN npm run build

# serve
WORKDIR /app
EXPOSE 31415
CMD ["python3", "explorer_server.py"]
