# system testing — Kafka and Pub/Sub inputs

Input-specific guidance for system-testing data streams that use `kafka` or `gcp-pubsub` inputs. Load `system-testing.md` (generic) first.

## Kafka

### Overview

Kafka system tests run a real Kafka broker (Kraft mode) alongside an `elastic/stream` producer that publishes sample log lines to a topic. The Elastic Agent consumes from the topic using the `kafka` input.

### Docker Compose pattern

```yaml
version: '2.3'
services:
  kafka-service:
    image: bashj79/kafka-kraft
    healthcheck:
      test: nc -z kafka-service 9094 || exit -1
      interval: 10s
      timeout: 5s
      retries: 15
    environment:
      KAFKA_LISTENERS: "INTERNAL://kafka-service:9092,EXTERNAL://:9094,CONTROLLER://:9093"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka-service:9092,EXTERNAL://kafka-service:9094"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "CONTROLLER:PLAINTEXT,EXTERNAL:PLAINTEXT,INTERNAL:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
    ports:
      - 9094

  <package>-<stream>-producer:
    image: docker.elastic.co/observability/stream:v0.18.0
    volumes:
      - ./sample_logs:/sample_logs:ro
    command:
      - log
      - --retry=30
      - --addr=kafka-service:9094
      - -p=kafka
      - --kafka-topic=<topic_name>
      - /sample_logs/<logfile>.log
    depends_on:
      kafka-service:
        condition: service_healthy
```

### Test config pattern

```yaml
wait_for_data_timeout: 1m
service: kafka-service
input: kafka
data_stream:
  vars:
    topics:
      - <topic_name>
    hosts:
      - "{{Hostname}}:{{Port}}"
    group_id: system_test
```

### Key patterns

- **`service: kafka-service`**: the test config references the broker service, not the producer
- **`{{Hostname}}:{{Port}}`**: resolved by the test runner to the broker's advertised address
- **`--retry=30`**: the producer retries connecting to the broker since it may take time to become healthy
- **`depends_on` with `service_healthy`**: ensures the broker is ready before the producer starts
- **`--kafka-topic`**: must match the `topics` list in the test config

## GCP Pub/Sub

### Overview

Pub/Sub system tests use the Google Cloud Pub/Sub emulator alongside an `elastic/stream` publisher. The Elastic Agent consumes messages using the `gcp-pubsub` input pointed at the emulator.

### Docker Compose pattern

```yaml
version: '2.3'
services:
  gcppubsub-emulator:
    image: google/cloud-sdk:emulators
    command: gcloud beta emulators pubsub start --host-port=0.0.0.0:8681
    ports:
      - "8681/tcp"

  <package>-<stream>-publisher:
    image: docker.elastic.co/observability/stream:v0.18.0
    volumes:
      - ./sample_logs:/sample_logs:ro
    command:
      - log
      - --retry=30
      - --addr=gcppubsub-emulator:8681
      - -p=gcppubsub
      - --gcppubsub-clear=true
      - --gcppubsub-project=<project_id>
      - /sample_logs/<logfile>.log
    depends_on:
      - gcppubsub-emulator
```

### Test config pattern

```yaml
wait_for_data_timeout: 1m
service: gcppubsub-emulator
input: gcp-pubsub
vars:
  alternative_host: "{{Hostname}}:{{Port}}"
  credentials_json: >-
    {"type":"service_account","project_id":"<project_id>"}
  project_id: <project_id>
  subscription_name: subscription
  topic: topic
```

### Key patterns

- **`alternative_host`**: points the agent at the emulator instead of real GCP
- **`--gcppubsub-clear=true`**: resets the emulator state before publishing
- **`credentials_json`**: a stub service account credential sufficient for the emulator

## Reference integrations

- [`kafka_log`](https://github.com/elastic/integrations/tree/main/packages/kafka_log) — Kafka Kraft broker with stream producer
- [`gcp_pubsub`](https://github.com/elastic/integrations/tree/main/packages/gcp_pubsub) — Pub/Sub emulator with stream publisher
