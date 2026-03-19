from des import EventQueue
from net import Generator, Join, Delay, MMCK, Reverse, IdGenerator
from stats import StatCollector
from utils import estimate_latency
from balancer import RoundRobinBalancer
import matplotlib.pyplot as plt


# Tweak values
IN = 300
MAX_QUEUE = 32

DC_CONFIGS = [
    ('dc1', 115, 2),
    ('dc2', 100, 2),
    ('dc3', 200, 2),
]

DISTANCES = {
    ('dc1', 'dc2'): 370000,
    ('dc2', 'dc3'): 220000,
    ('dc3', 'dc1'): 315000,
}

INNER_DISTANCE = 1000
LATENCY_SCALE = 1_000_000

START_TIME = 10_000_000
END_TIME = 100_000_000
STAT_INTERVAL = 500_000

event_queue = EventQueue()
id_gen = IdGenerator()

# Store components
generators = {}
balancers = {}
servers = {}
joins = {}
terms = {}
delays = {}
stats = {}

latencies = {}
for (src, dst), dist in DISTANCES.items():
    latencies[(src, dst)] = estimate_latency(dist, 'fiber') * LATENCY_SCALE
    latencies[(dst, src)] = latencies[(src, dst)]
for dc in [n for n, _, _ in DC_CONFIGS]:
    latencies[(dc, dc)] = estimate_latency(INNER_DISTANCE) * LATENCY_SCALE


for name, mu, pods in DC_CONFIGS:
    gen = Generator(f'{name}_in', id_gen, IN)
    generators[name] = gen

    bal = RoundRobinBalancer(f'{name}_bal', 6)
    balancers[name] = bal
    gen.connect(bal)

    join = Join(f'{name}_join')
    server = MMCK(f'{name}_server', mu, pods, MAX_QUEUE)
    term = Reverse(f'{name}_term')

    join.connect(server)
    server.connect(term)

    joins[name] = join
    terms[name] = term
    servers[name] = server

for src in [n for n, _, _ in DC_CONFIGS]:
    for dst in [n for n, _, _ in DC_CONFIGS]:
        delay_name = f'{src}_{dst}_delay'
        delay = Delay(delay_name, latencies[(src, dst)])
        delay.connect(joins[dst])
        delays[(src, dst)] = delay
        balancers[src].connect(delay)

for name in generators:
    gen = generators[name]
    gen.set_event_queue(event_queue)
    gen.verify()

for name in [n for n, _, _ in DC_CONFIGS]:
    dc_stat = StatCollector(generators[name], STAT_INTERVAL)
    bal_stat = StatCollector(balancers[name], STAT_INTERVAL)

    dc_stat.start(event_queue, START_TIME)
    bal_stat.start(event_queue, START_TIME)

    stats[f'{name}_in'] = dc_stat
    stats[f'{name}_bal'] = bal_stat

for gen in generators.values():
    gen.start()

while True:
    event = event_queue.process_event()
    if event is None or event.timestamp > END_TIME:
        break

# Plot stats
fig, axes = plt.subplots(3, 2, figsize=(10, 8))

# Map DC names to indices
dc_names = ['dc1', 'dc2', 'dc3']
for i, name in enumerate(dc_names):
    ax_stats = axes[i][0]
    ax_timings = axes[i][1]

    ax_stats.set_yscale('log')
    stat_collector = stats[f'{name}_in']
    stat_collector.plot_stats(['dropped', 'received', 'generated'], ax=ax_stats)
    stat_collector.plot_timings([95, 98, 99, 99.5, 99.8, 99.9], ax=ax_timings)

plt.tight_layout()
plt.show()

# Plot balancer stats
fig, axes = plt.subplots(3, 1, figsize=(10, 8))
for i, name in enumerate(dc_names):
    bal_stat = stats[f'{name}_bal']
    bal_stat.plot_stats(['successes', 'retries', 'failures'], ax=axes[i])

plt.tight_layout()
plt.show()

# Print final stats
for name in dc_names:
    gen = generators[name]
    server = servers[name]
    bal = balancers[name]

    print(f"\n--- {name.upper()} Stats ---")
    print(f"Generator: {gen.stat}")
    print(f"Server: {server.stat}")
    print(f"Balancer: {bal.stat}")
