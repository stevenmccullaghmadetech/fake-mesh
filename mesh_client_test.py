from __future__ import absolute_import, print_function
from unittest import TestCase, main
import random
import signal
import sys
import traceback
from mesh_client import MeshClient, MeshError, default_ssl_opts


def print_stack_frames(signum=None, frame=None):
    for frame in sys._current_frames().values():
        traceback.print_stack(frame)
        print()


signal.signal(signal.SIGUSR1, print_stack_frames)


class TestError(Exception):
    pass


class MeshClientTest(TestCase):
    uri = 'https://localhost:8829'

    def setUp(self):
        self.alice_mailbox = str(random.randint(0, 1000000000000))
        self.bob_mailbox = str(random.randint(0, 1000000000000))
        self.alice = MeshClient(
            self.uri,
            self.alice_mailbox,
            'password',
            max_chunk_size=5,
            **default_ssl_opts)
        self.bob = MeshClient(
            self.uri,
            self.bob_mailbox,
            'password',
            max_chunk_size=5,
            **default_ssl_opts)

    def test_handshake(self):
        alice = self.alice

        hand_shook = alice.handshake()
        self.assertEqual(hand_shook, b"hello")

    def test_send_receive(self):
        alice = self.alice
        bob = self.bob

        message_id = alice.send_message(self.bob_mailbox, b"Hello Bob 1")
        self.assertEqual([message_id], bob.list_messages())
        msg = bob.retrieve_message(message_id)
        self.assertEqual(msg.read(), b"Hello Bob 1")
        self.assertEqual(msg.sender, self.alice_mailbox)
        self.assertEqual(msg.recipient, self.bob_mailbox)
        msg.acknowledge()
        self.assertEqual([], bob.list_messages())

    def test_line_by_line(self):
        alice = self.alice
        bob = self.bob

        message_id = alice.send_message(self.bob_mailbox, b"Hello Bob 1\nHello Bob 2")
        self.assertEqual([message_id], bob.list_messages())
        msg = bob.retrieve_message(message_id)
        self.assertEqual(list(iter(msg)), [b"Hello Bob 1\n", b"Hello Bob 2"])

    def test_readline(self):
        alice = self.alice
        bob = self.bob

        message_id = alice.send_message(self.bob_mailbox, b"Hello Bob 1\nHello Bob 2")
        self.assertEqual([message_id], bob.list_messages())
        msg = bob.retrieve_message(message_id)
        self.assertEqual(msg.readline(), b"Hello Bob 1\n")

    def test_readlines(self):
        alice = self.alice
        bob = self.bob

        message_id = alice.send_message(self.bob_mailbox, b"Hello Bob 1\nHello Bob 2")
        self.assertEqual([message_id], bob.list_messages())
        msg = bob.retrieve_message(message_id)
        self.assertEqual(msg.readlines(), [b"Hello Bob 1\n", b"Hello Bob 2"])

    def test_transparent_compression(self):
        alice = self.alice
        bob = self.bob

        print("Sending")
        alice._transparent_compress = True
        message_id = alice.send_message(
            self.bob_mailbox, b"Hello Bob Compressed")
        self.assertEqual([message_id], bob.list_messages())
        print("Receiving")
        msg = bob.retrieve_message(message_id)
        self.assertEqual(msg.read(), b"Hello Bob Compressed")
        self.assertEqual(msg.mex_header('from'), self.alice_mailbox)
        msg.acknowledge()
        self.assertEqual([], bob.list_messages())

    def test_iterate_and_context_manager(self):
        alice = self.alice
        bob = self.bob

        alice.send_message(self.bob_mailbox, b"Hello Bob 2")
        alice.send_message(self.bob_mailbox, b"Hello Bob 3")
        messages_read = 0
        for (msg, expected) in zip(bob.iterate_all_messages(),
                                   [b"Hello Bob 2", b"Hello Bob 3"]):
            with msg:
                self.assertEqual(msg.read(), expected)
                messages_read += 1
        self.assertEqual(2, messages_read)
        self.assertEqual([], bob.list_messages())

    def test_context_manager_failure(self):
        alice = self.alice
        bob = self.bob

        message_id = alice.send_message(self.bob_mailbox, b"Hello Bob 4")
        try:
            with bob.retrieve_message(message_id) as msg:
                self.assertEqual(msg.read(), b"Hello Bob 4")
                raise TestError()
        except TestError:
            pass
        self.assertEqual([message_id], bob.list_messages())

    def test_optional_args(self):
        alice = self.alice
        bob = self.bob

        message_id = alice.send_message(
            self.bob_mailbox,
            b"Hello Bob 5",
            subject="Hello World",
            filename="upload.txt",
            local_id="12345",
            message_type="DATA",
            process_id="321",
            workflow_id="111",
            encrypted=False,
            compressed=False)

        with bob.retrieve_message(message_id) as msg:
            self.assertEqual(msg.subject, "Hello World")
            self.assertEqual(msg.filename, "upload.txt")
            self.assertEqual(msg.local_id, "12345")
            self.assertEqual(msg.message_type, "DATA")
            self.assertEqual(msg.process_id, "321")
            self.assertEqual(msg.workflow_id, "111")
            self.assertFalse(msg.encrypted)
            self.assertFalse(msg.compressed)

        message_id = alice.send_message(
            self.bob_mailbox, b"Hello Bob 5", encrypted=True, compressed=True)

        with bob.retrieve_message(message_id) as msg:
            self.assertTrue(msg.encrypted)
            self.assertTrue(msg.compressed)


if __name__ == "__main__":
    main()
