from des import EventQueue
from net import Generator, Join, Delay, MMCK, Reverse, IdGenerator
from stats import StatCollector
from utils import estimate_latency
from balancer import RoundRobinBalancer
import matplotlib.pyplot as plt


# Tweak values
IN = 300  # 150
MAX_QUEUE = 32

DC1_MU = 115
DC1_PODS = 2

DC2_MU = 100
DC2_PODS = 2

DC3_MU = 200
DC3_PODS = 2

START_TIME = 10_000_000
END_TIME = 100_000_000

event_queue = EventQueue()
id_gen = IdGenerator()

# Generators
dc1_in = Generator('dc1_in', id_gen, IN)
dc2_in = Generator('dc2_in', id_gen, IN)
dc3_in = Generator('dc3_in', id_gen, IN)

# DC balancers
# Checkout balancer.py for various types of balancers
dc1_bal = RoundRobinBalancer('dc1_bal', 6)
dc2_bal = RoundRobinBalancer('dc2_bal', 6)
dc3_bal = RoundRobinBalancer('dc3_bal', 6)

dc1_in.connect(dc1_bal)
dc2_in.connect(dc2_bal)
dc3_in.connect(dc3_bal)

# DC backends
dc1_join = Join('dc1_join')
dc2_join = Join('dc2_join')
dc3_join = Join('dc3_join')
dc1_server = MMCK('dc1_server',  DC1_MU, DC1_PODS, MAX_QUEUE)
dc2_server = MMCK('dc2_server',  DC2_MU, DC2_PODS, MAX_QUEUE)
dc3_server = MMCK('dc3_server',  DC3_MU, DC3_PODS, MAX_QUEUE)
dc1_term = Reverse('dc1_term')
dc2_term = Reverse('dc2_term')
dc3_term = Reverse('dc3_term')

dc1_join.connect(dc1_server)
dc2_join.connect(dc2_server)
dc3_join.connect(dc3_server)
dc1_server.connect(dc1_term)
dc2_server.connect(dc2_term)
dc3_server.connect(dc3_term)

# Cross DC delays
dc1_dc2_latency = estimate_latency(370000, 'fiber') * 1_000_000
dc2_dc3_latency = estimate_latency(220000, 'fiber') * 1_000_000
dc3_dc1_latency = estimate_latency(315000, 'fiber') * 1_000_000
inner_latency = estimate_latency(1000) * 1_000_000

dc1_dc1_delay = Delay('dc1_dc1_delay', inner_latency)
dc1_dc2_delay = Delay('dc1_dc2_delay', dc1_dc2_latency)
dc1_dc3_delay = Delay('dc1_dc3_delay', dc3_dc1_latency)

dc2_dc1_delay = Delay('dc2_dc1_delay', dc1_dc2_latency)
dc2_dc2_delay = Delay('dc2_dc2_delay', inner_latency)
dc2_dc3_delay = Delay('dc2_dc3_delay', dc2_dc3_latency)

dc3_dc1_delay = Delay('dc3_dc1_delay', dc3_dc1_latency)
dc3_dc2_delay = Delay('dc3_dc2_delay', dc2_dc3_latency)
dc3_dc3_delay = Delay('dc3_dc3_delay', inner_latency)

dc1_dc1_delay.connect(dc1_join)
dc1_dc2_delay.connect(dc2_join)
dc1_dc3_delay.connect(dc3_join)

dc2_dc1_delay.connect(dc1_join)
dc2_dc2_delay.connect(dc2_join)
dc2_dc3_delay.connect(dc3_join)

dc3_dc1_delay.connect(dc1_join)
dc3_dc2_delay.connect(dc2_join)
dc3_dc3_delay.connect(dc3_join)

dc1_bal.connect(dc1_dc1_delay)
dc1_bal.connect(dc1_dc2_delay)
dc1_bal.connect(dc1_dc3_delay)

dc2_bal.connect(dc2_dc1_delay)
dc2_bal.connect(dc2_dc2_delay)
dc2_bal.connect(dc2_dc3_delay)

dc3_bal.connect(dc3_dc1_delay)
dc3_bal.connect(dc3_dc2_delay)
dc3_bal.connect(dc3_dc3_delay)

# Connect everything
dc1_in.set_event_queue(event_queue)
dc2_in.set_event_queue(event_queue)
dc3_in.set_event_queue(event_queue)

dc1_in.verify()
dc2_in.verify()
dc3_in.verify()

dc1_stat = StatCollector(dc1_in, 500_000)
dc2_stat = StatCollector(dc2_in, 500_000)
dc3_stat = StatCollector(dc3_in, 500_000)

dc1_bal_stat = StatCollector(dc1_bal, 500_000)
dc2_bal_stat = StatCollector(dc2_bal, 500_000)
dc3_bal_stat = StatCollector(dc3_bal, 500_000)

dc1_stat.start(event_queue, START_TIME)
dc2_stat.start(event_queue, START_TIME)
dc3_stat.start(event_queue, START_TIME)

dc1_bal_stat.start(event_queue, START_TIME)
dc2_bal_stat.start(event_queue, START_TIME)
dc3_bal_stat.start(event_queue, START_TIME)

dc1_in.start()
dc2_in.start()
dc3_in.start()

while True:
    event = event_queue.process_event()
    if event is None or event.timestamp > END_TIME:
        break

# Plot stats
fig, axes = plt.subplots(3, 2, figsize=(10, 8))
axes[0][0].set_yscale('log')
dc1_stat.plot_stats(['dropped', 'received', 'generated'], ax=axes[0][0])
dc1_stat.plot_timings([95, 98, 99, 99.5, 99.8, 99.9], ax=axes[0][1])

axes[1][0].set_yscale('log')
dc2_stat.plot_stats(['dropped', 'received', 'generated'], ax=axes[1][0])
dc2_stat.plot_timings([95, 98, 99, 99.5, 99.8, 99.9], ax=axes[1][1])

axes[2][0].set_yscale('log')
dc3_stat.plot_stats(['dropped', 'received', 'generated'], ax=axes[2][0])
dc3_stat.plot_timings([95, 98, 99, 99.5, 99.8, 99.9], ax=axes[2][1])
plt.tight_layout()
plt.show()

fig, axes = plt.subplots(3, 1, figsize=(10, 8))
dc1_bal_stat.plot_stats(['successes', 'retries', 'failures'], ax=axes[0])
dc2_bal_stat.plot_stats(['successes', 'retries', 'failures'], ax=axes[1])
dc3_bal_stat.plot_stats(['successes', 'retries', 'failures'], ax=axes[2])
plt.tight_layout()
plt.show()

print(dc1_in.stat)
print(dc2_in.stat)
print(dc3_in.stat)

print(dc1_server.stat)
print(dc2_server.stat)
print(dc3_server.stat)

print(dc1_bal.stat)
print(dc2_bal.stat)
print(dc3_bal.stat)
