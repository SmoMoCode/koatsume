#!/usr/bin/env python3
"""
Network module for TCP/UDP dual-port streaming between peers
"""

import socket
import struct
import threading
import time
from typing import Optional, Dict, Callable, Tuple


class UDPPacket:
    """UDP packet format handler"""
    
    # Packet types
    TYPE_HEARTBEAT = 0
    TYPE_MOUSE_ABSOLUTE = 1
    
    # Struct formats
    HEADER_FORMAT = "!HB"  # sequence (uint16), type (uint8)
    MOUSE_FORMAT = "!HHbbB"  # x (uint16), y (uint16), wheel_x (int8), wheel_y (int8), buttons (uint8)
    
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MOUSE_SIZE = struct.calcsize(MOUSE_FORMAT)
    
    @staticmethod
    def pack_heartbeat(sequence: int) -> bytes:
        """Pack a heartbeat packet"""
        return struct.pack(UDPPacket.HEADER_FORMAT, sequence, UDPPacket.TYPE_HEARTBEAT)
    
    @staticmethod
    def pack_mouse_absolute(sequence: int, x: int, y: int, 
                           wheel_x: int, wheel_y: int, buttons: int) -> bytes:
        """Pack a mouse absolute position packet"""
        header = struct.pack(UDPPacket.HEADER_FORMAT, sequence, UDPPacket.TYPE_MOUSE_ABSOLUTE)
        payload = struct.pack(UDPPacket.MOUSE_FORMAT, x, y, wheel_x, wheel_y, buttons)
        return header + payload
    
    @staticmethod
    def unpack(data: bytes) -> Optional[Dict]:
        """Unpack a UDP packet"""
        if len(data) < UDPPacket.HEADER_SIZE:
            return None
        
        sequence, packet_type = struct.unpack(UDPPacket.HEADER_FORMAT, data[:UDPPacket.HEADER_SIZE])
        
        if packet_type == UDPPacket.TYPE_HEARTBEAT:
            return {
                'sequence': sequence,
                'type': 'heartbeat'
            }
        elif packet_type == UDPPacket.TYPE_MOUSE_ABSOLUTE:
            if len(data) < UDPPacket.HEADER_SIZE + UDPPacket.MOUSE_SIZE:
                return None
            
            x, y, wheel_x, wheel_y, buttons = struct.unpack(
                UDPPacket.MOUSE_FORMAT, 
                data[UDPPacket.HEADER_SIZE:UDPPacket.HEADER_SIZE + UDPPacket.MOUSE_SIZE]
            )
            
            return {
                'sequence': sequence,
                'type': 'mouse_absolute',
                'x': x,
                'y': y,
                'wheel_x': wheel_x,
                'wheel_y': wheel_y,
                'buttons': buttons
            }
        
        return None


class TCPMessage:
    """TCP message format handler"""
    
    @staticmethod
    def pack_handshake(tcp_port: int, udp_port: int, username: str) -> bytes:
        """Pack a handshake message"""
        data = {
            'type': 'handshake',
            'tcp_port': tcp_port,
            'udp_port': udp_port,
            'username': username
        }
        import json
        return json.dumps(data).encode() + b'\n'
    
    @staticmethod
    def pack_sync(rx_packets: int, rx_bytes: int, last_rx_time: float) -> bytes:
        """Pack a sync/stats message"""
        data = {
            'type': 'sync',
            'rx_packets': rx_packets,
            'rx_bytes': rx_bytes,
            'last_rx_time': last_rx_time
        }
        import json
        return json.dumps(data).encode() + b'\n'
    
    @staticmethod
    def unpack(data: bytes) -> Optional[Dict]:
        """Unpack a TCP message"""
        try:
            import json
            return json.loads(data.decode())
        except Exception:
            return None


class PeerConnection:
    """Manages connection to a single peer"""
    
    def __init__(self, peer_name: str, peer_address: str, 
                 tcp_port: int, udp_port: int,
                 local_tcp_port: int, local_udp_port: int,
                 username: str,
                 on_mouse_data: Optional[Callable] = None,
                 on_disconnect: Optional[Callable] = None):
        self.peer_name = peer_name
        self.peer_address = peer_address
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.local_tcp_port = local_tcp_port
        self.local_udp_port = local_udp_port
        self.username = username
        self.on_mouse_data = on_mouse_data
        self.on_disconnect = on_disconnect
        
        self.running = False
        self.connected = False
        
        # Statistics
        self.tx_sequence = 0
        self.rx_packets = 0
        self.rx_bytes = 0
        self.last_tx_time = 0
        self.last_rx_time = 0
        
        # Sockets
        self.tcp_socket = None
        self.udp_socket = None
        
        # Threads
        self.tcp_thread = None
        self.udp_tx_thread = None
        self.udp_rx_thread = None
        self.heartbeat_thread = None
        
        # Mouse state
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_wheel_x = 0
        self.mouse_wheel_y = 0
        self.mouse_buttons = 0
    
    def start(self):
        """Start the peer connection"""
        self.running = True
        
        # Create UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('0.0.0.0', self.local_udp_port))
        self.udp_socket.settimeout(0.1)
        
        # Start threads
        self.udp_tx_thread = threading.Thread(target=self._udp_transmit_loop, daemon=True)
        self.udp_tx_thread.start()
        
        self.udp_rx_thread = threading.Thread(target=self._udp_receive_loop, daemon=True)
        self.udp_rx_thread.start()
        
        self.tcp_thread = threading.Thread(target=self._tcp_connect_and_sync, daemon=True)
        self.tcp_thread.start()
        
        self.heartbeat_thread = threading.Thread(target=self._check_liveness, daemon=True)
        self.heartbeat_thread.start()
        
        print(f"Started peer connection to {self.peer_name} at {self.peer_address}:{self.tcp_port}/{self.udp_port}")
    
    def stop(self):
        """Stop the peer connection"""
        self.running = False
        self.connected = False
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception:
                pass
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception:
                pass
        
        print(f"Stopped peer connection to {self.peer_name}")
    
    def update_mouse_state(self, x: int, y: int, wheel_x: int = 0, wheel_y: int = 0, buttons: int = 0):
        """Update the mouse state to be transmitted"""
        self.mouse_x = x
        self.mouse_y = y
        self.mouse_wheel_x = wheel_x
        self.mouse_wheel_y = wheel_y
        self.mouse_buttons = buttons
    
    def _tcp_connect_and_sync(self):
        """Connect to peer via TCP and send periodic sync messages"""
        while self.running:
            try:
                # Try to connect
                self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_socket.settimeout(2.0)
                self.tcp_socket.connect((self.peer_address, self.tcp_port))
                
                # Send handshake
                handshake = TCPMessage.pack_handshake(self.local_tcp_port, self.local_udp_port, self.username)
                self.tcp_socket.sendall(handshake)
                
                self.connected = True
                print(f"TCP connected to {self.peer_name}")
                
                # Read handshake response
                buffer = b''
                while self.running:
                    chunk = self.tcp_socket.recv(1024)
                    if not chunk:
                        break
                    
                    buffer += chunk
                    if b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        msg = TCPMessage.unpack(line)
                        if msg and msg.get('type') == 'handshake':
                            print(f"Received handshake from {self.peer_name}: {msg}")
                            break
                
                # Sync loop - send stats every 1 second
                while self.running:
                    time.sleep(1.0)
                    
                    sync_msg = TCPMessage.pack_sync(self.rx_packets, self.rx_bytes, self.last_rx_time)
                    try:
                        self.tcp_socket.sendall(sync_msg)
                        self.last_tx_time = time.time()
                    except Exception as e:
                        print(f"Error sending TCP sync to {self.peer_name}: {e}")
                        break
                
            except Exception as e:
                print(f"TCP connection error to {self.peer_name}: {e}")
                self.connected = False
                
                if self.tcp_socket:
                    try:
                        self.tcp_socket.close()
                    except Exception:
                        pass
                    self.tcp_socket = None
                
                # Wait before reconnecting
                time.sleep(2.0)
    
    def _udp_transmit_loop(self):
        """Transmit UDP packets at 1000 Hz"""
        while self.running:
            try:
                # Send mouse state packet
                packet = UDPPacket.pack_mouse_absolute(
                    self.tx_sequence,
                    self.mouse_x,
                    self.mouse_y,
                    self.mouse_wheel_x,
                    self.mouse_wheel_y,
                    self.mouse_buttons
                )
                
                self.udp_socket.sendto(packet, (self.peer_address, self.udp_port))
                
                self.tx_sequence = (self.tx_sequence + 1) % 65536
                self.last_tx_time = time.time()
                
                # 1000 Hz = 1 ms interval
                time.sleep(0.001)
                
            except Exception as e:
                print(f"UDP transmit error to {self.peer_name}: {e}")
                time.sleep(0.1)
    
    def _udp_receive_loop(self):
        """Receive UDP packets"""
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                
                self.rx_packets += 1
                self.rx_bytes += len(data)
                self.last_rx_time = time.time()
                
                packet = UDPPacket.unpack(data)
                if packet:
                    if packet['type'] == 'mouse_absolute' and self.on_mouse_data:
                        self.on_mouse_data(self.peer_name, packet)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"UDP receive error from {self.peer_name}: {e}")
                time.sleep(0.1)
    
    def _check_liveness(self):
        """Check if peer is still alive"""
        while self.running:
            time.sleep(0.5)
            
            current_time = time.time()
            
            # Check if we received any traffic (TCP or UDP) in the last 2 seconds
            time_since_rx = current_time - self.last_rx_time if self.last_rx_time > 0 else 999
            time_since_tx = current_time - self.last_tx_time if self.last_tx_time > 0 else 999
            
            if self.last_rx_time > 0 and time_since_rx > 2.0:
                print(f"Peer {self.peer_name} timed out (no RX for {time_since_rx:.1f}s)")
                if self.on_disconnect:
                    self.on_disconnect(self.peer_name)
                break


class NetworkManager:
    """Manages all peer connections"""
    
    def __init__(self, username: str, on_mouse_data: Optional[Callable] = None):
        self.username = username
        self.on_mouse_data = on_mouse_data
        
        # Port allocation
        self.base_tcp_port = 50000
        self.base_udp_port = 51000
        self.next_port_offset = 0
        
        # Peer connections
        self.peers: Dict[str, PeerConnection] = {}
        self.peers_lock = threading.Lock()
        
        # TCP listener for incoming connections
        self.tcp_listener = None
        self.tcp_listener_thread = None
        self.running = False
    
    def start(self):
        """Start the network manager"""
        self.running = True
        
        # Start TCP listener for incoming handshakes
        self.tcp_listener_thread = threading.Thread(target=self._tcp_listener_loop, daemon=True)
        self.tcp_listener_thread.start()
    
    def stop(self):
        """Stop the network manager"""
        self.running = False
        
        # Stop all peer connections
        with self.peers_lock:
            for peer in list(self.peers.values()):
                peer.stop()
            self.peers.clear()
        
        if self.tcp_listener:
            try:
                self.tcp_listener.close()
            except Exception:
                pass
    
    def connect_to_peer(self, peer_name: str, peer_address: str, peer_port: int):
        """Initiate connection to a discovered peer"""
        with self.peers_lock:
            if peer_name in self.peers:
                return  # Already connected
            
            # Allocate ports for this peer
            tcp_port = self.base_tcp_port + self.next_port_offset
            udp_port = self.base_udp_port + self.next_port_offset
            self.next_port_offset += 1
            
            # Create peer connection
            peer = PeerConnection(
                peer_name=peer_name,
                peer_address=peer_address,
                tcp_port=peer_port if peer_port > 0 else 50000,
                udp_port=peer_port + 1000 if peer_port > 0 else 51000,
                local_tcp_port=tcp_port,
                local_udp_port=udp_port,
                username=self.username,
                on_mouse_data=self._handle_mouse_data,
                on_disconnect=self._handle_peer_disconnect
            )
            
            self.peers[peer_name] = peer
            peer.start()
    
    def disconnect_peer(self, peer_name: str):
        """Disconnect from a peer"""
        with self.peers_lock:
            if peer_name in self.peers:
                peer = self.peers[peer_name]
                peer.stop()
                del self.peers[peer_name]
    
    def update_mouse_state(self, x: int, y: int, wheel_x: int = 0, wheel_y: int = 0, buttons: int = 0):
        """Update mouse state for all peers"""
        with self.peers_lock:
            for peer in self.peers.values():
                peer.update_mouse_state(x, y, wheel_x, wheel_y, buttons)
    
    def _handle_mouse_data(self, peer_name: str, packet: Dict):
        """Handle received mouse data from a peer"""
        if self.on_mouse_data:
            self.on_mouse_data(peer_name, packet)
    
    def _handle_peer_disconnect(self, peer_name: str):
        """Handle peer disconnection"""
        print(f"Peer {peer_name} disconnected, cleaning up")
        self.disconnect_peer(peer_name)
    
    def _tcp_listener_loop(self):
        """Listen for incoming TCP connections"""
        # For now, we're initiating connections only
        # In a full implementation, we'd listen for incoming connections here
        pass
