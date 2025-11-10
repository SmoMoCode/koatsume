#!/usr/bin/env python3
"""
Mouse capture module for reading mouse state
"""

import threading
import time
from typing import Optional, Callable

try:
    from pynput import mouse
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("Warning: pynput not available, mouse capture will use simulated data")


class MouseCapture:
    """Captures mouse state and provides it to the network layer"""
    
    def __init__(self, on_mouse_update: Optional[Callable] = None):
        self.on_mouse_update = on_mouse_update
        self.running = False
        
        # Current mouse state
        self.x = 0
        self.y = 0
        self.buttons = 0
        self.wheel_x = 0
        self.wheel_y = 0
        
        # Listener
        self.listener = None
        self.update_thread = None
    
    def start(self):
        """Start capturing mouse state"""
        self.running = True
        
        if PYNPUT_AVAILABLE:
            # Use pynput to capture mouse events
            self.listener = mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click,
                on_scroll=self._on_scroll
            )
            self.listener.start()
        else:
            # Use simulated mouse data
            self.update_thread = threading.Thread(target=self._simulate_mouse, daemon=True)
            self.update_thread.start()
    
    def stop(self):
        """Stop capturing mouse state"""
        self.running = False
        
        if self.listener:
            self.listener.stop()
    
    def _on_move(self, x, y):
        """Called when mouse moves"""
        self.x = max(0, min(65535, int(x)))
        self.y = max(0, min(65535, int(y)))
        self._notify_update()
    
    def _on_click(self, x, y, button, pressed):
        """Called when mouse button is clicked"""
        # Update button bitfield
        button_bit = 0
        if hasattr(button, 'left') and button == mouse.Button.left:
            button_bit = 1 << 0
        elif hasattr(button, 'right') and button == mouse.Button.right:
            button_bit = 1 << 1
        elif hasattr(button, 'middle') and button == mouse.Button.middle:
            button_bit = 1 << 2
        
        if pressed:
            self.buttons |= button_bit
        else:
            self.buttons &= ~button_bit
        
        self._notify_update()
    
    def _on_scroll(self, x, y, dx, dy):
        """Called when mouse wheel scrolls"""
        # Accumulate wheel delta
        self.wheel_x = max(-128, min(127, self.wheel_x + int(dx)))
        self.wheel_y = max(-128, min(127, self.wheel_y + int(dy)))
        self._notify_update()
    
    def _notify_update(self):
        """Notify callback of mouse state update"""
        if self.on_mouse_update:
            self.on_mouse_update(self.x, self.y, self.wheel_x, self.wheel_y, self.buttons)
        
        # Reset wheel deltas after notification
        self.wheel_x = 0
        self.wheel_y = 0
    
    def _simulate_mouse(self):
        """Simulate mouse movement for testing"""
        import math
        t = 0
        while self.running:
            # Simulate circular mouse movement
            self.x = int(32768 + 10000 * math.cos(t))
            self.y = int(32768 + 10000 * math.sin(t))
            t += 0.01
            
            self._notify_update()
            time.sleep(0.1)
    
    def get_state(self):
        """Get current mouse state"""
        return {
            'x': self.x,
            'y': self.y,
            'wheel_x': self.wheel_x,
            'wheel_y': self.wheel_y,
            'buttons': self.buttons
        }
