"""Exercise parallel TCP integrity and cancellation against real loopback peers.

No board, Docker, host NIC configuration or fixed listening ports are used.
"""
import contextlib
import importlib.util
from pathlib import Path
import socket
import socketserver
import sys
import threading
import time
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('ethernet_peer', Path(__file__).resolve().parents[1]/'ethernet/peer.py')
network = importlib.util.module_from_spec(spec)
spec.loader.exec_module(network)

@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux TCP_INFO contract')
class EthernetPeer(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self, source=False, corrupt=False):
        counts = {'received': 0}
        lock = threading.Lock()
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(2)
                try:
                    if source:
                        body = bytes(range(256))*64
                        if corrupt:
                            body = bytes([255])+body[1:]
                        while True:
                            self.request.sendall(body)
                    else:
                        received = 0
                        while True:
                            body = self.request.recv(32768)
                            if not body:
                                break
                            expected = (bytes(range(256))*129)[received & 255:(received & 255)+len(body)]
                            if body != expected:
                                raise AssertionError('Client sent incorrect pattern')
                            received += len(body)
                            with lock:
                                counts['received'] += len(body)
                except (ConnectionError, socket.timeout):
                    pass
        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
        server = Server(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
        thread.start()
        class Peer(network.Peer):
            def __init__(self):
                self.board = self.host = '127.0.0.1'
            def reset(self, run):
                counts['received'] = 0
            def stats(self):
                return {'tcp_rx_bytes': counts['received'], 'tcp_bad_chunks': 0}
        connect = socket.create_connection
        def local_connection(address, **kwargs):
            return connect(server.server_address, **kwargs)
        try:
            with mock.patch.object(network.socket, 'create_connection', side_effect=local_connection):
                yield Peer(), counts
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_four_receive_streams_have_exact_aggregate_count(self):
        with self.fixture() as (peer, counts):
            result = peer.tcp_trial('pc_to_som', .1, 4)
        self.assertEqual(result['streams'], 4)
        self.assertGreater(result['received_bytes'], 0)
        self.assertEqual(result['received_bytes'], counts['received'])
        self.assertEqual(result['received_bytes'], sum(c['bytes'] for c in result['connections']))

    def test_four_transmit_streams_verify_their_own_pattern_offsets(self):
        with self.fixture(source=True) as (peer, _):
            result = peer.tcp_trial('som_to_pc', .1, 4)
        self.assertTrue(all(c['bytes'] > 0 for c in result['connections']))

    def test_parallel_corruption_fails_and_closes_workers_promptly(self):
        start = time.monotonic()
        with self.fixture(source=True, corrupt=True) as (peer, _):
            with self.assertRaisesRegex(RuntimeError, 'TCP payload mismatch'):
                peer.tcp_trial('som_to_pc', 30, 4)
        self.assertLess(time.monotonic()-start, 3)
