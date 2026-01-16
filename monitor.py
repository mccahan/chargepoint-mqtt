#!/usr/bin/env python3
"""
ChargePoint to MQTT Monitor
Monitors ChargePoint EV chargers and publishes status to MQTT topics.
"""

from __future__ import annotations

import os
import sys
import time
import logging
from typing import Optional

import paho.mqtt.client as mqtt
from python_chargepoint import ChargePoint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ChargePoint status constants
STATUS_CHARGING = 'CHARGING'
STATUS_INUSE = 'INUSE'
STATUS_AVAILABLE = 'AVAILABLE'


class ChargePointMQTTMonitor:
    """Monitor ChargePoint chargers and publish to MQTT."""
    
    def __init__(self):
        """Initialize the monitor with configuration from environment variables."""
        # ChargePoint credentials
        self.cp_username = os.getenv('CHARGEPOINT_USERNAME')
        self.cp_password = os.getenv('CHARGEPOINT_PASSWORD')
        
        # MQTT configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.mqtt_username = os.getenv('MQTT_USERNAME')
        self.mqtt_password = os.getenv('MQTT_PASSWORD')
        self.mqtt_client_id = os.getenv('MQTT_CLIENT_ID', 'chargepoint-mqtt')
        
        # MQTT topic configuration
        self.mqtt_topic_prefix = os.getenv('MQTT_TOPIC_PREFIX', 'chargepoint')
        self.mqtt_topic_connected = os.getenv('MQTT_TOPIC_CONNECTED', f'{self.mqtt_topic_prefix}/connected')
        self.mqtt_topic_power = os.getenv('MQTT_TOPIC_POWER', f'{self.mqtt_topic_prefix}/power')
        
        # Poll interval in seconds
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '60'))
        
        # Validate required configuration
        if not self.cp_username or not self.cp_password:
            logger.error("CHARGEPOINT_USERNAME and CHARGEPOINT_PASSWORD must be set")
            sys.exit(1)
        
        # Initialize clients
        self.chargepoint = None
        self.mqtt_client = None
        
    def setup_mqtt(self):
        """Set up MQTT client connection."""
        # Use CallbackAPIVersion.VERSION1 for compatibility with paho-mqtt >= 2.0
        try:
            from paho.mqtt.client import CallbackAPIVersion
            self.mqtt_client = mqtt.Client(
                client_id=self.mqtt_client_id,
                callback_api_version=CallbackAPIVersion.VERSION1
            )
        except (ImportError, AttributeError):
            # Fallback for paho-mqtt < 2.0
            self.mqtt_client = mqtt.Client(client_id=self.mqtt_client_id)
        
        if self.mqtt_username and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        try:
            logger.info(f"Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            sys.exit(1)
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback for when MQTT client connects."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
        else:
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback for when MQTT client disconnects."""
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection. Code: {rc}")
    
    def setup_chargepoint(self):
        """Set up ChargePoint client."""
        try:
            logger.info("Logging in to ChargePoint")
            self.chargepoint = ChargePoint(self.cp_username, self.cp_password)
        except Exception as e:
            logger.error(f"Failed to log in to ChargePoint: {e}")
            sys.exit(1)
    
    def publish_status(self, connected: int, power_watts: float):
        """
        Publish charger status to MQTT topics.
        
        Args:
            connected: 1 if charger is connected, 0 otherwise
            power_watts: Current power output in watts
        """
        try:
            # Publish connected status (0 or 1)
            self.mqtt_client.publish(
                self.mqtt_topic_connected,
                str(connected),
                retain=True
            )
            logger.debug(f"Published connected status: {connected}")
            
            # Publish power in watts
            self.mqtt_client.publish(
                self.mqtt_topic_power,
                str(power_watts),
                retain=True
            )
            logger.debug(f"Published power: {power_watts}W")
            
        except Exception as e:
            logger.error(f"Failed to publish to MQTT: {e}")
    
    def get_charger_status(self) -> tuple[int, float]:
        """
        Get the current status of the charger.
        
        Returns:
            Tuple of (connected status as 0/1, power in watts)
        """
        try:
            # Get home chargers
            chargers = self.chargepoint.get_home_chargers()
            
            if not chargers:
                logger.warning("No home chargers found")
                return 0, 0.0
            
            # For now, monitor the first charger
            # In the future, this could be extended to monitor multiple chargers
            # chargers is a list of device IDs (integers), not dictionaries
            device_id = chargers[0]
            
            logger.debug(f"Monitoring device_id: {device_id}")
            
            # Get charger details/status
            status = self.chargepoint.get_charging_status(device_id)
            
            # Determine if connected (charging or plugged in)
            # Status could be: 'AVAILABLE', 'CHARGING', 'INUSE', etc.
            charging_status = status.get('status', STATUS_AVAILABLE).upper()
            connected = 1 if charging_status in [STATUS_CHARGING, STATUS_INUSE] else 0
            
            # Get current power output in watts
            # The API might return power in kW, so convert to watts
            power_kw = status.get('power', 0.0) or 0.0
            power_watts = float(power_kw) * 1000.0
            
            logger.info(f"Charger status: connected={connected}, power={power_watts}W")
            
            return connected, power_watts
            
        except Exception as e:
            logger.error(f"Error getting charger status: {e}")
            return 0, 0.0
    
    def run(self):
        """Run the monitoring loop."""
        logger.info("Starting ChargePoint MQTT Monitor")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        logger.info(f"MQTT topics: {self.mqtt_topic_connected}, {self.mqtt_topic_power}")
        
        self.setup_mqtt()
        self.setup_chargepoint()
        
        try:
            while True:
                connected, power_watts = self.get_charger_status()
                self.publish_status(connected, power_watts)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()


def main():
    """Main entry point."""
    monitor = ChargePointMQTTMonitor()
    monitor.run()


if __name__ == '__main__':
    main()
