from __future__ import absolute_import, print_function
from unittest import TestCase, main
import random
import signal
import sys
import threading
import traceback
from mesh_client import MeshClient, MeshError, default_ssl_opts
from fake_mesh.server import make_server


def print_stack_frames(signum=None, frame=None):
    for frame in sys._current_frames().values():
        traceback.print_stack(frame)
        print()


signal.signal(signal.SIGUSR1, print_stack_frames)


class TestError(Exception):
    pass


class MeshClientTest(TestCase):
    uri = 'https://localhost:8829'

    @classmethod
    def setUpClass(cls):
        cls.server = make_server(host='127.0.0.1', port=8829, logging=True)
        cls.server_thread = threading.Thread(target=cls.server.start)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.server_thread.join()

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
        self.assertEqual(msg.filename, message_id + '.dat')
        msg.acknowledge()
        self.assertEqual([], bob.list_messages())

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

    def test_endpoint_lookup(self):
        result = self.alice.lookup_endpoint('ORG1', 'WF1')
        result_list = result['results']
        self.assertEqual(len(result_list), 1)
        self.assertEqual(result_list[0]['address'], 'ORG1HC001')
        self.assertEqual(result_list[0]['description'], 'ORG1 WF1 endpoint')
        self.assertEqual(result_list[0]['endpoint_type'], 'MESH')

    def test_tracking(self):
        alice = self.alice
        bob = self.bob
        tracking_id = 'Message1'
        msg_id = alice.send_message(self.bob_mailbox, b'Hello World', local_id=tracking_id)
        self.assertEqual(alice.get_tracking_info(message_id=msg_id)['status'], 'Accepted')
        self.assertIsNone(alice.get_tracking_info(message_id=msg_id)['downloadTimestamp'])
        bob.retrieve_message(msg_id).read()
        self.assertIsNotNone(alice.get_tracking_info(message_id=msg_id)['downloadTimestamp'])
        bob.acknowledge_message(msg_id)
        self.assertEqual(alice.get_tracking_info(message_id=msg_id)['status'], 'Acknowledged')

    def test_msg_id_tracking(self):
        alice = self.alice
        bob = self.bob
        msg_id = alice.send_message(self.bob_mailbox, b'Hello World')
        self.assertEqual(alice.get_tracking_info(message_id=msg_id)['status'], 'Accepted')
        self.assertIsNone(alice.get_tracking_info(message_id=msg_id)['downloadTimestamp'])
        bob.retrieve_message(msg_id).read()
        self.assertIsNotNone(alice.get_tracking_info(message_id=msg_id)['downloadTimestamp'])
        bob.acknowledge_message(msg_id)
        self.assertEqual(alice.get_tracking_info(message_id=msg_id)['status'], 'Acknowledged')


if __name__ == "__main__":
    main()
