# koatsume
An app to connect lots of little things together.

## Features

- **Peer Discovery**: Automatic discovery of other Koatsume instances on the local network using mDNS/Zeroconf
- **Dual-Port Streaming**: TCP and UDP communication between peers
  - TCP (port 50000): Control channel for handshakes, peer identification, and 1 Hz sync messages
  - UDP (port 51000): High-frequency data channel streaming mouse state at 1000 Hz
- **Mouse State Sharing**: Real-time mouse position and button state streaming between peers
- **GUI Display**: Web-based interface showing discovered peers and their mouse data

## Security Considerations

### Network Binding
The application binds TCP and UDP sockets to `0.0.0.0` (all network interfaces) to enable:
- Discovery and communication from any network interface on the machine
- LAN-wide peer discovery and streaming

This is intentional for a local network application. The security relies on:
1. **Network Isolation**: The application is designed for trusted local networks only
2. **Limited Scope**: Zeroconf/mDNS discovery is limited to the local network segment
3. **No Authentication**: Currently, the application does not implement authentication (suitable for trusted networks)

**Recommendation**: Only run this application on trusted networks. Do not expose these ports to the public internet.

### Packet Format
- UDP packets use binary network byte order (big-endian) with struct
- No encryption is currently implemented
- Suitable for trusted LAN environments only

## Usage

```bash
pip install -r requirements.txt
python app.py
```

The application will:
1. Start TCP listener on port 50000
2. Start UDP socket on port 51000
3. Register itself via mDNS for peer discovery
4. Open a GUI showing discovered peers
5. Stream mouse state to connected peers at 1000 Hz
