# Data Center Simulation with Discrete-Event System

This project implements a discrete-event simulation of a distributed network of data centers. The system models request generation, routing, network latency, load balancing, and server processing under constrained queue capacity. Performance metrics such as throughput, latency, and failure rates are collected.

## Overview

The simulation consists of three interconnected data centers (dc1, dc2, dc3), each capable of generating incoming requests and processing both local and remote workloads. Requests are routed to other data centers based on physical distance, which determines network transmission delay. Each data center employs load balancer and a multi-server queueing model with finite buffer capacity.

The simulation runs over a defined time interval, collecting statistics at regular intervals. Results are visualized using plots and printed summaries to evaluate system behavior under the given configuration.

## Configuration Parameters

### Data Center Specifications
Each data center is defined by its name, service rate (μ in requests per second), and number of processing pods (servers).

```python
DC_CONFIGS = [
    ('dc1', 115, 2),
    ('dc2', 100, 2),
    ('dc3', 200, 2),
]
```

### Network Distances
Physical distances between data centers (in meters) are used to compute transmission latency assuming fiber-optic propagation speed.

```python
DISTANCES = {
    ('dc1', 'dc2'): 370000,
    ('dc2', 'dc3'): 220000,
    ('dc3', 'dc1'): 315000,
}
```

Internal latency within the same data center is modeled using a fixed distance of 1000 meters.

### Simulation Settings
- Request input rate: 300 requests per second (`IN = 300`)
- Maximum queue size per server: 32 (`MAX_QUEUE = 32`)
- Simulation end time: 100,000,000 microseconds (100 seconds - `END_TIME`)
- Statistics collestion start time: 10,000,000 microseconds (10 seconds - `START_TIME`)
- Statistics collection interval: 500,000 microseconds (0.5 seconds - `STAT_INTERVAL`)

## System Components

- **Generator**: Produces new requests at a constant rate for each data center.
- **Fork**: Distributes outgoing requests across destinations.
- **Join**: Aggregates incoming requests from multiple sources (e.g., local generator and remote data centers)
into a single stream before routing to the server/
- **Delay**: Introduces propagation delay based on estimated latency derived from distance.
- **MMCK Server**: Multi-server queueing system with C servers and K maximum queue size (including those in service).
- **Reverse**: Handles the reverse path of processed requests, typically used to model response flow back through the network. It ensures that after processing, responses are correctly routed back through delays and balancers to their origin or next hop.
- **StatCollector**: Collects and aggregates performance metrics over time.
- **EventQueue**: Core discrete-event scheduler that manages the execution of events in chronological order.

## Output and Analysis

### Plots

Two primary figures are generated:

1. **Per-Data Center Traffic and Latency**
   - Left column: Time series of generated, received, and dropped requests (log scale).
   - Right column: Percentile end-to-end response times (95, 98, 99, 99.5, 99.8, 99.9).

2. **Load Balancer Statistics**
   - Successes, retries, and failures for each data center's load balancer over time.

### Console Output

At the end of the simulation, summary statistics are printed for each data center:
- Generator statistics: generated, received, dropped
- Server statistics: received, dropped, processed
- Balancer statistics: successes, retries, failures

## Customization

The following parameters can be adjusted at the top of the script to modify system behavior:

| Parameter         | Description |
|-------------------|-------------|
| IN                | Request generation rate (requests per second) |
| MAX_QUEUE         | Maximum number of requests in server queue |
| DC_CONFIGS        | List of (name, service_rate, num_pods) |
| DISTANCES         | Inter-DC distances in meters |
| INNER_DISTANCE    | Assumed internal distance for intra-DC latency |
| START_TIME        | Start of simulation (microseconds) |
| END_TIME          | End of simulation (microseconds) |
| STAT_INTERVAL     | Frequency of statistic collection (microseconds) |
