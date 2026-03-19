# rbcapp1 - Service Monitoring Assignment

## About

rbcapp1 depends on 3 services: httpd, rabbitMQ and postgreSQL. If any goes down, the app is considered DOWN. This project monitors those services and stores their status in Elasticsearch.

**Note:** I used Docker to set this up since I don't have a dedicated Linux server. All the scripts and playbooks are written for Linux (RHEL/CentOS) and will work the same way on an actual Linux machine with systemd.

## Structure

```
.
├── docker-compose.yml       # spins up ES, httpd, rabbitmq, postgres, flask
├── Dockerfile
├── test1/
│   ├── service_monitor.py   # checks services via systemctl, writes JSON
│   ├── app.py               # REST API - POST /add, GET /healthcheck
│   └── requirements.txt
├── test2/
│   ├── inventory            # hosts file for ansible
│   └── assignment.yml       # playbook (verify_install, check-disk, check-status)
└── test3/
    ├── filter_sales.py      # filters CSV by avg price/sqft
    └── Assignment_python.csv
```

## Setup

Need Docker Desktop running and python3 installed.

```
docker compose up --build -d
```

Wait till elasticsearch is healthy:
```
docker compose ps
```

## TEST 1a - Service Monitor

```
docker exec -it rbcapp1-app bash
cd /app/test1/
python3 service_monitor.py
```

Creates JSON files in `status_output/`. Services show DOWN in docker since there's no systemd — on a real RHEL box they'd show actual status.

## TEST 1b - REST API

Flask starts automatically with docker compose.

Add service statuses:
```
curl -X POST http://localhost:5000/add -H "Content-Type: application/json" -d '{"service_name":"httpd","service_status":"UP","host_name":"host1"}'

curl -X POST http://localhost:5000/add -H "Content-Type: application/json" -d '{"service_name":"rabbitmq-server","service_status":"UP","host_name":"host1"}'

curl -X POST http://localhost:5000/add -H "Content-Type: application/json" -d '{"service_name":"postgresql","service_status":"UP","host_name":"host1"}'
```

Check status:
```
curl http://localhost:5000/healthcheck
curl http://localhost:5000/healthcheck/httpd
```

Can also upload the JSON files from the monitor script via file upload:
```
curl -X POST http://localhost:5000/add -F "file=@status_output/httpd-status-20260319T081707Z.json"
```

## TEST 2 - Ansible

Syntax check:
```
ansible-playbook assignment.yml -i inventory --syntax-check
```

Three actions:

```
ansible-playbook assignment.yml -i inventory -e action=verify_install
ansible-playbook assignment.yml -i inventory -e action=check-disk
ansible-playbook assignment.yml -i inventory -e action=check-status
```

check-status works locally against the running Flask API. The other two need actual RHEL hosts with SSH — update the IPs in inventory file.

## TEST 3 - CSV Filter

```
cd test3/
python3 filter_sales.py
```

Reads sales data, calculates avg price/sqft ($145.67), writes filtered CSV with 470 records below that average. No dependencies needed, just python stdlib.

## Cleanup

```
docker compose down -v
```
