# inventory_service
A small service for demonstrating Python 3.12 features

# Local development in Docker

For running local version of inventory_service you may install Docker Engine(or Docker Desktop)
https://docs.docker.com/engine/

After that, just run following command
```
$ sudo docker compose up --build
```

And then visit in your browser swagger docs:

http://localhost:8080/swagger/


# Monitoring & performance tests

You can run a simple Locust performance test against inventory_service using Locust web UI:

http://localhost:8089/

All infrastructure components are monitoring through Prometheus, you can inspect all the metrics using default Prometheus UI:

http://localhost:9090/graph

Or you can add your own dashboard in Grafana(or import existing from src/perf_tests/grafana/)

http://localhost:3000/

Login credentials to grafana you may found in `docker-compose.yml`.
