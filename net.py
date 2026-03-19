from __future__ import annotations
from dataclasses import dataclass
from typing import override
import des
import random


class Message:
    def __init__(self, id: int):
        self.id: int = id
        self.timestamp: int = 0
        self.type: str = "normal"


class Node:
    def __init__(self, name: str):
        self.name: str = name
        self.left: list[Node] = []
        self.right: list[Node] = []
        self.event_queue: des.EventQueue | None = None

    def connect(self, node: Node):
        if node in self.left or self in node.right:
            raise Exception((
                f'Tried to form loop between "{self.name} "'
                f'and Node "{node.name}"'
            ))

        if node in self.right or self in node.left:
            raise Exception(
                f'Duplicate link between "{self.name}" and "{node.name}"'
            )

        self.right.append(node)
        node.left.append(self)

    def on_message(self, node: Node, message: Message, side: str):
        del node, message, side

    def verify(self):
        for other in self.right:
            other.verify()

    def set_event_queue(self, event_queue: des.EventQueue):
        self.event_queue = event_queue
        for other in self.right:
            other.set_event_queue(event_queue)

    def send(self, node: Node, message: Message):
        if node not in self.left and node not in self.right:
            raise Exception((
                f'Tried to send message from "{self.name}" to '
                f'"{node.name}" without link'
            ))

        direction = "right" if node in self.left else "left"
        node.on_message(self, message, direction)


class Delay(Node):
    @dataclass
    class Event(des.Event):
        node: Delay
        target: Node
        message: Message

        @override
        def process(self, queue: des.EventQueue):
            self.node.send(self.target, self.message)

    def __init__(self, name: str, delay: int, jitter: int = 0):
        Node.__init__(self, name)
        self.delay: int = delay
        self.jitter: int = jitter

    @override
    def verify(self):
        if len(self.left) != 1:
            raise Exception(
                f'Delay node "{self.name}" must have exactly one left node'
            )
        if len(self.right) != 1:
            raise Exception((
                f'Delay node "{self.name}" must have exactly one '
                f"right node"
            ))
        super().verify()

    @override
    def on_message(self, node: Node, message: Message, side: str):
        if not self.event_queue:
            raise Exception('event_queue was not set')

        timestamp = des.event_timestamp(
            self.event_queue.timestamp, 0, self.delay
        )
        timestamp += random.randint(-self.jitter, self.jitter)

        if side == "right":
            self.event_queue.add_event(
                Delay.Event(timestamp, self, self.left[0], message)
            )
        else:
            self.event_queue.add_event(
                Delay.Event(timestamp, self, self.right[0], message)
            )


class Fork(Node):
    def __init__(self, name: str):
        super().__init__(name)

    @override
    def verify(self):
        if len(self.left) != 1:
            raise Exception(
                f'Fork node "{self.name}" must have exactly one left node'
            )
        if len(self.right) < 1:
            raise Exception(
                f'Fork node "{self.name}" must have at least one right node'
            )
        super().verify()

    @override
    def on_message(self, node: Node, message: Message, side: str):
        if side == "right":
            self.send(self.left[0], message)
            return

        target = random.choice(self.right)
        self.send(target, message)


class Join(Node):
    def __init__(self, name: str):
        super().__init__(name)
        self.origin: dict[int, Node] = {}

    @override
    def verify(self):
        if len(self.left) < 1:
            raise Exception(
                f'Join node "{self.name}" must have at least one left node'
            )
        if len(self.right) != 1:
            raise Exception(
                f'Join node "{self.name}" must have exactly one right node'
            )
        super().verify()

    @override
    def on_message(self, node: Node, message: Message, side: str):
        if side == "right":
            original_node = self.origin.pop(message.id, None)
            if original_node is not None:
                self.send(original_node, message)
            return

        self.origin[message.id] = node
        self.send(self.right[0], message)


class MMCK(Node):
    @dataclass
    class Process(des.Event):
        node: MMCK
        message: Message

        @override
        def process(self, queue: des.EventQueue):
            self.node._complete_service(self.message)

    @dataclass
    class Timeout(des.Event):
        node: MMCK
        message: Message

        @override
        def process(self, queue: des.EventQueue):
            if self.message not in self.node.queue:
                return

            self.node.queue.remove(self.message)
            dropped_msg = Message(id=self.message.id)
            dropped_msg.timestamp = self.message.timestamp
            dropped_msg.type = "dropped"
            self.node.stat["dropped"] += 1
            self.node.send(self.node.left[0], dropped_msg)

    def __init__(
        self,
        name: str,
        service_rate: float,
        num_servers: int,
        capacity: int | None = None,
        timeout: int | None = None,
    ):
        super().__init__(name)
        self.service_rate: float = service_rate
        self.num_servers: int = num_servers
        self.capacity: int | None = capacity
        self.timeout: int | None = timeout
        self.queue: list[Message] = []
        self.in_service: int = 0
        self.stat: dict[str, int] = {
            "received": 0,
            "dropped": 0,
            "processed": 0,
        }

    @override
    def verify(self):
        if len(self.left) != 1:
            raise Exception(
                f'MMCK node "{self.name}" must have exactly one left node'
            )
        if len(self.right) != 1:
            raise Exception(
                f'MMCK node "{self.name}" must have exactly one right node'
            )
        super().verify()

    @override
    def on_message(self, node: Node, message: Message, side: str):
        if not self.event_queue:
            raise Exception('event_queue was not set')

        if side == "right":
            self.send(self.left[0], message)
            return

        self.stat["received"] += 1
        if (
            self.capacity
            and len(self.queue) + self.in_service >= self.capacity
        ):
            self.stat["dropped"] += 1
            dropped_msg = Message(id=message.id)
            dropped_msg.timestamp = message.timestamp
            dropped_msg.type = "dropped"
            self.send(self.left[0], dropped_msg)
            return

        if self.timeout:
            timestamp = self.event_queue.timestamp + self.timeout
            event = MMCK.Timeout(timestamp, self, message)
            self.event_queue.add_event(event)

        self.queue.append(message)
        self._start_service()

    def _start_service(self):
        if not self.event_queue:
            raise Exception('event_queue was not set')

        if not self.queue or self.in_service >= self.num_servers:
            return

        msg = self.queue.pop(0)
        self.in_service += 1

        timestamp = des.event_timestamp(
            self.event_queue.timestamp, self.service_rate, 0
        )
        event = MMCK.Process(timestamp, self, msg)
        self.event_queue.add_event(event)

    def _complete_service(self, message: Message):
        self.stat["processed"] += 1
        self.in_service -= 1
        self.send(self.right[0], message)
        self._start_service()


class IdGenerator:
    def __init__(self):
        self.counter: int = 0

    def next_id(self) -> int:
        current = self.counter
        self.counter += 1
        return current


class Generator(Node):
    @dataclass
    class Event(des.Event):
        generator: Generator

        @override
        def process(self, queue: des.EventQueue):
            self.generator.next_message()
            next_timestamp = des.event_timestamp(
                queue.timestamp, self.generator.service_rate
            )
            queue.add_event(Generator.Event(next_timestamp, self.generator))

    def __init__(
        self, name: str, id_generator: IdGenerator, service_rate: float
    ):
        super().__init__(name)
        self.id_generator: IdGenerator = id_generator
        self.service_rate: float = service_rate
        self.stat: dict[str, int] = {
            "generated": 0,
            "received": 0,
            "dropped": 0
        }
        self.timing: list[int] = []

    def next_message(self):
        if not self.event_queue:
            raise Exception('event_queue was not set')

        self.stat["generated"] += 1
        message = Message(self.id_generator.next_id())
        message.timestamp = self.event_queue.timestamp
        self.send(self.right[0], message)

    @override
    def verify(self):
        if len(self.left) != 0:
            raise Exception((
                f'Generator node "{self.name}" must have exactly zero left '
                f"nodes"
            ))
        if len(self.right) != 1:
            raise Exception((
                f'Generator node "{self.name}" must have exactly one right '
                f"node"
            ))
        super().verify()

    @override
    def on_message(self, node: Node, message: Message, side: str):
        if not self.event_queue:
            raise Exception('event_queue was not set')

        self.timing.append(self.event_queue.timestamp - message.timestamp)
        self.stat["received"] += 1
        if message.type != "normal":
            self.stat["dropped"] += 1

    def start(self):
        if not self.event_queue:
            raise Exception('event_queue was not set')

        next_timestamp = self.event_queue.timestamp
        self.event_queue.add_event(Generator.Event(next_timestamp, self))


class Reverse(Node):
    def __init__(self, name: str):
        super().__init__(name)

    @override
    def verify(self):
        if len(self.left) != 1:
            raise Exception(
                f'Reverse node "{self.name}" must have exactly one left node'
            )
        if len(self.right) != 0:
            raise Exception((
                f'Reverse node "{self.name}" must have exactly zero right '
                f"nodes"
            ))
        super().verify()

    @override
    def on_message(self, node: Node, message: Message, side: str):
        self.send(self.left[0], message)
