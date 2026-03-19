from net import Fork, Node, Message

import random


class RetryingBalancer(Fork):
    def __init__(self, name: str, max_retries: int = 1):
        super().__init__(name)
        self.max_retries = max_retries
        self.outstanding = {}

        self.stat = {
            'successes': 0,
            'retries': 0,
            'failures': 0,
            'total': 0
        }

    def on_message(self, node: Node, message: Message, side: str):
        if side == "right":
            # Response from a backend
            msg_id = message.id

            if message.type == "dropped":
                # Request was rejected
                if msg_id in self.outstanding:
                    original_msg, retry_count = self.outstanding[msg_id]
                    del self.outstanding[msg_id]

                    if retry_count < self.max_retries:
                        self._retry_message(original_msg, retry_count + 1)
                    else:
                        # Out of retries - final failure
                        self.stat['failures'] += 1
                        self.stat['total'] += 1
                        self.send(self.left[0], message)
                else:
                    # Unknown dropped message
                    self.stat['failures'] += 1
                    self.stat['total'] += 1
                    self.send(self.left[0], message)
            else:
                # Success
                if msg_id in self.outstanding:
                    del self.outstanding[msg_id]
                self.stat['successes'] += 1
                self.stat['total'] += 1
                self.send(self.left[0], message)

            return

        # new incoming message
        self._send_first_attempt(message)

    def _send_first_attempt(self, message: Message):
        target = random.choice(self.right)
        self.outstanding[message.id] = (message, 0)  # (msg, retry_count)
        self.send(target, message)

    def _retry_message(self, message: Message, retry_count: int):
        target = random.choice(self.right)

        self.outstanding[message.id] = (message, retry_count)
        self.stat['retries'] += 1
        self.send(target, message)


class RoundRobinBalancer(Fork):
    def __init__(self, name: str, max_retries: int = 1):
        super().__init__(name)
        self.max_retries = max_retries
        self.next_index = 0
        self.outstanding = {}
        self.stat = {
            'successes': 0,
            'retries': 0,
            'failures': 0,
            'total': 0
        }

    def _next_backend(self):
        backend = self.right[self.next_index]
        self.next_index = (self.next_index + 1) % len(self.right)
        return backend

    def _send_first_attempt(self, message: Message):
        target = self._next_backend()
        self.outstanding[message.id] = (message, 0)
        self.send(target, message)

    def _retry_message(self, message: Message, retry_count: int):
        target = self._next_backend()
        self.outstanding[message.id] = (message, retry_count)
        self.stat['retries'] += 1
        self.send(target, message)

    def on_message(self, node: Node, message: Message, side: str):
        if side == "right":
            msg_id = message.id

            if message.type == "dropped":
                # Request failed
                if msg_id in self.outstanding:
                    original_msg, retry_count = self.outstanding[msg_id]
                    del self.outstanding[msg_id]

                    if retry_count < self.max_retries:
                        # Retry using next backend in rotation
                        self._retry_message(original_msg, retry_count + 1)
                    else:
                        # Out of retries
                        self.stat['failures'] += 1
                        self.stat['total'] += 1
                        self.send(self.left[0], message)
                else:
                    # Unknown dropped message
                    self.stat['failures'] += 1
                    self.stat['total'] += 1
                    self.send(self.left[0], message)
            else:
                # Success
                if msg_id in self.outstanding:
                    del self.outstanding[msg_id]
                self.stat['successes'] += 1
                self.stat['total'] += 1
                self.send(self.left[0], message)

            return

        self._send_first_attempt(message)
