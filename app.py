#!/usr/bin/env python3
"""
Koatsume - Connect lots of little things together
A cross-platform application using PyWebView with Material UI interface
"""

import json
import os
import threading
import time
from pathlib import Path

import webview
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf


class KoatsumeApp:
    """Main application class for Koatsume"""
    
    def __init__(self):
        self.config_file = Path("config.json")
        self.config = self.load_config()
        self.discovered_instances = []
        self.hidden_instances = set()  # Track instances hidden by user
        self.zeroconf = None
        self.browser = None
        self.service_info = None
        self.window = None
        self.heartbeat_thread = None
        self.running = True
        
    def load_config(self):
        """Load configuration from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {"username": ""}
    
    def save_config(self):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_username(self):
        """Get the current username"""
        return self.config.get("username", "")
    
    def set_username(self, username):
        """Set and persist the username"""
        self.config["username"] = username
        self.save_config()
        self.update_service()
        return {"status": "success", "username": username}
    
    def get_discovered_instances(self):
        """Get list of discovered instances"""
        current_time = time.time()
        result = []
        for instance in self.discovered_instances:
            # Skip hidden instances
            if instance["name"] in self.hidden_instances:
                continue
            
            # Calculate if instance is connected (seen within last 1 second)
            time_since_seen = current_time - instance["last_seen"]
            instance_copy = instance.copy()
            instance_copy["connected"] = time_since_seen <= 1.0
            instance_copy["time_since_seen"] = time_since_seen
            result.append(instance_copy)
        
        return result
    
    def hide_instance(self, name):
        """Hide an instance from the view"""
        self.hidden_instances.add(name)
        # Update UI if window exists
        if self.window:
            self.window.evaluate_js('updateInstances()')
        return {"status": "success"}
    
    def add_discovered_instance(self, info):
        """Add a discovered instance to the list"""
        import socket
        
        # Convert addresses to human-readable format
        addresses = []
        for addr in info.addresses:
            try:
                if len(addr) == 4:  # IPv4
                    addresses.append(socket.inet_ntoa(addr))
                elif len(addr) == 16:  # IPv6
                    addresses.append(socket.inet_ntop(socket.AF_INET6, addr))
            except Exception:
                addresses.append(addr.hex())
        
        current_time = time.time()
        instance = {
            "name": info.name,
            "server": info.server,
            "addresses": addresses,
            "port": info.port,
            "properties": {k.decode(): v.decode() for k, v in info.properties.items()} if info.properties else {},
            "last_seen": current_time,
            "connected": True
        }
        
        # Check if already exists
        for i, existing in enumerate(self.discovered_instances):
            if existing["name"] == instance["name"]:
                # Update existing instance with fresh timestamp
                instance["last_seen"] = current_time
                instance["connected"] = True
                self.discovered_instances[i] = instance
                # Remove from hidden list if it reappears
                self.hidden_instances.discard(instance["name"])
                return
        
        self.discovered_instances.append(instance)
        # Remove from hidden list if it reappears
        self.hidden_instances.discard(instance["name"])
        
        # Update UI if window exists
        if self.window:
            self.window.evaluate_js('updateInstances()')
    
    def remove_discovered_instance(self, name):
        """Remove a discovered instance from the list"""
        self.discovered_instances = [i for i in self.discovered_instances if i["name"] != name]
        
        # Update UI if window exists
        if self.window:
            self.window.evaluate_js('updateInstances()')
    
    def check_heartbeat(self):
        """Periodically check instance heartbeats"""
        while self.running:
            time.sleep(0.5)  # Check every 500ms to match UI update frequency
            if self.window:
                try:
                    self.window.evaluate_js('updateInstances()')
                except Exception:
                    pass
    
    def start_zeroconf(self):
        """Start zeroconf service discovery"""
        self.zeroconf = Zeroconf()
        
        # Register our service
        self.register_service()
        
        # Browse for other instances
        listener = ServiceListener(self)
        self.browser = ServiceBrowser(self.zeroconf, "_koatsume._tcp.local.", listener)
        
        # Start heartbeat checking thread
        self.heartbeat_thread = threading.Thread(target=self.check_heartbeat, daemon=True)
        self.heartbeat_thread.start()
    
    def register_service(self):
        """Register this instance as a zeroconf service"""
        import socket
        
        hostname = socket.gethostname()
        username = self.config.get("username", "Anonymous")
        
        # Create service info
        service_name = f"koatsume-{hostname}._koatsume._tcp.local."
        
        # Get local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = '127.0.0.1'
        finally:
            s.close()
        
        # Parse IP address - handle both IPv4 and IPv6
        try:
            # Try IPv4 first
            if ':' not in local_ip:
                addresses = [socket.inet_aton(local_ip)]
            else:
                # IPv6
                addresses = [socket.inet_pton(socket.AF_INET6, local_ip)]
        except Exception as e:
            print(f"Error parsing IP address {local_ip}: {e}")
            addresses = [socket.inet_aton('127.0.0.1')]
        
        self.service_info = ServiceInfo(
            "_koatsume._tcp.local.",
            service_name,
            addresses=addresses,
            port=0,  # We're not actually listening on a port yet
            properties={b"username": username.encode()},
            server=f"{hostname}.local."
        )
        
        try:
            self.zeroconf.register_service(self.service_info)
            print(f"Registered service: {service_name}")
        except Exception as e:
            print(f"Error registering service: {e}")
    
    def update_service(self):
        """Update the zeroconf service when username changes"""
        if self.service_info and self.zeroconf:
            try:
                self.zeroconf.unregister_service(self.service_info)
            except Exception:
                pass
            self.register_service()
    
    def stop_zeroconf(self):
        """Stop zeroconf service"""
        self.running = False
        
        if self.service_info and self.zeroconf:
            try:
                self.zeroconf.unregister_service(self.service_info)
            except Exception:
                pass
        
        if self.zeroconf:
            self.zeroconf.close()


class ServiceListener:
    """Listener for zeroconf service discovery"""
    
    def __init__(self, app):
        self.app = app
    
    def add_service(self, zeroconf, service_type, name):
        """Called when a service is discovered"""
        info = zeroconf.get_service_info(service_type, name)
        if info:
            print(f"Service added: {name}")
            self.app.add_discovered_instance(info)
    
    def remove_service(self, zeroconf, service_type, name):
        """Called when a service is removed"""
        print(f"Service removed: {name}")
        self.app.remove_discovered_instance(name)
    
    def update_service(self, zeroconf, service_type, name):
        """Called when a service is updated"""
        info = zeroconf.get_service_info(service_type, name)
        if info:
            print(f"Service updated: {name}")
            self.app.add_discovered_instance(info)


def get_html():
    """Generate the HTML interface"""
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Koatsume</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        }
        
        h1 {
            color: #667eea;
            font-size: 32px;
            margin-bottom: 8px;
        }
        
        .subtitle {
            color: #666;
            font-size: 16px;
        }
        
        .username-section {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        }
        
        .input-group {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        
        label {
            font-size: 16px;
            font-weight: 500;
            color: #333;
            min-width: 100px;
        }
        
        input[type="text"] {
            flex: 1;
            padding: 12px 16px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            transition: all 0.3s;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        }
        
        button {
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 500;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        button:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        .instances-section {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        }
        
        h2 {
            color: #333;
            font-size: 24px;
            margin-bottom: 16px;
        }
        
        .instances-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }
        
        .instance-tile {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: all 0.3s;
            position: relative;
        }
        
        .instance-tile:nth-child(2n) {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        
        .instance-tile:nth-child(3n) {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }
        
        .instance-tile:nth-child(4n) {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }
        
        .instance-tile:nth-child(5n) {
            background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
        }
        
        .instance-tile:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
        }
        
        .instance-tile.disconnected {
            position: relative;
            filter: grayscale(100%);
            opacity: 0.7;
        }
        
        .instance-tile.disconnected::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(128, 128, 128, 0.4);
            border-radius: 12px;
            pointer-events: none;
        }
        
        .close-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            border: 2px solid rgba(0, 0, 0, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 20px;
            font-weight: bold;
            transition: all 0.2s;
            z-index: 10;
        }
        
        .close-btn:hover {
            background: rgba(255, 255, 255, 1);
            transform: scale(1.1);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }
        
        .instance-name {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 8px;
            word-break: break-word;
        }
        
        .instance-info {
            font-size: 14px;
            opacity: 0.95;
        }
        
        .instance-server {
            margin-top: 4px;
            font-size: 12px;
            opacity: 0.85;
        }
        
        .instance-status {
            margin-top: 8px;
            font-size: 13px;
            font-weight: 500;
            opacity: 0.9;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        
        .status-message {
            margin-top: 12px;
            padding: 12px;
            border-radius: 8px;
            font-size: 14px;
            display: none;
        }
        
        .status-message.success {
            background: #d4edda;
            color: #155724;
            display: block;
        }
        
        .status-message.error {
            background: #f8d7da;
            color: #721c24;
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌟 Koatsume</h1>
            <p class="subtitle">Connect lots of little things together</p>
        </div>
        
        <div class="username-section">
            <div class="input-group">
                <label for="username">Username:</label>
                <input type="text" id="username" placeholder="Enter your username" />
                <button onclick="saveUsername()">Save</button>
            </div>
            <div id="status" class="status-message"></div>
        </div>
        
        <div class="instances-section">
            <h2>Discovered Instances</h2>
            <div id="instances" class="instances-grid">
                <div class="empty-state">
                    <div class="empty-state-icon">🔍</div>
                    <p>Looking for other Koatsume instances on your network...</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Load username on startup
        window.addEventListener('DOMContentLoaded', async () => {
            try {
                const username = await pywebview.api.get_username();
                document.getElementById('username').value = username;
            } catch (e) {
                console.error('Error loading username:', e);
            }
            
            // Start polling for instances
            updateInstances();
            setInterval(updateInstances, 500);  // Update every 500ms for responsive disconnection detection
        });
        
        async function saveUsername() {
            const username = document.getElementById('username').value;
            const status = document.getElementById('status');
            
            try {
                await pywebview.api.set_username(username);
                status.className = 'status-message success';
                status.textContent = 'Username saved successfully!';
                
                setTimeout(() => {
                    status.className = 'status-message';
                }, 3000);
            } catch (e) {
                status.className = 'status-message error';
                status.textContent = 'Error saving username: ' + e;
                console.error('Error:', e);
            }
        }
        
        function formatTimeSince(seconds) {
            if (seconds < 60) {
                return `${Math.floor(seconds)} seconds ago`;
            } else if (seconds < 3600) {
                const minutes = Math.floor(seconds / 60);
                return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
            } else if (seconds < 86400) {
                const hours = Math.floor(seconds / 3600);
                return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
            } else {
                const days = Math.floor(seconds / 86400);
                return `${days} day${days !== 1 ? 's' : ''} ago`;
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function hideInstance(name) {
            try {
                await pywebview.api.hide_instance(name);
            } catch (e) {
                console.error('Error hiding instance:', e);
            }
        }
        
        async function updateInstances() {
            try {
                const instances = await pywebview.api.get_discovered_instances();
                const container = document.getElementById('instances');
                
                if (instances.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">🔍</div>
                            <p>Looking for other Koatsume instances on your network...</p>
                        </div>
                    `;
                } else {
                    container.innerHTML = instances.map((instance, index) => {
                        const username = escapeHtml(instance.properties?.username || 'Unknown');
                        const disconnectedClass = instance.connected ? '' : 'disconnected';
                        const statusText = instance.connected 
                            ? '✅ Connected' 
                            : `⏰ Last seen ${formatTimeSince(instance.time_since_seen)}`;
                        const closeBtn = !instance.connected 
                            ? `<div class="close-btn" data-instance-index="${index}">✕</div>`
                            : '';
                        
                        return `
                            <div class="instance-tile ${disconnectedClass}" data-instance-name="${escapeHtml(instance.name)}">
                                ${closeBtn}
                                <div class="instance-name">👤 ${username}</div>
                                <div class="instance-info">📡 ${escapeHtml(instance.name.split('.')[0])}</div>
                                <div class="instance-server">🖥️ ${escapeHtml(instance.server)}</div>
                                <div class="instance-status">${statusText}</div>
                            </div>
                        `;
                    }).join('');
                    
                    // Add event listeners for close buttons
                    document.querySelectorAll('.close-btn').forEach(btn => {
                        btn.addEventListener('click', (e) => {
                            const tile = e.target.closest('.instance-tile');
                            const instanceName = tile.getAttribute('data-instance-name');
                            hideInstance(instanceName);
                        });
                    });
                }
            } catch (e) {
                console.error('Error updating instances:', e);
            }
        }
    </script>
</body>
</html>
    """


def main():
    """Main entry point"""
    app = KoatsumeApp()
    
    # Start zeroconf in a regular background thread for proper cleanup
    zeroconf_thread = threading.Thread(target=app.start_zeroconf, daemon=False)
    zeroconf_thread.start()
    
    # Create window
    app.window = webview.create_window(
        'Koatsume',
        html=get_html(),
        js_api=app,
        width=900,
        height=700,
        resizable=True
    )
    
    # Start the GUI (this blocks until window is closed)
    webview.start()
    
    # Cleanup after window is closed
    app.stop_zeroconf()


if __name__ == '__main__':
    main()
