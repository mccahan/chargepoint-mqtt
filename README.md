# chargepoint-mqtt

Output current home ChargePoint charger status to MQTT

This Docker container monitors your home ChargePoint EV charger and publishes the current status and power usage to MQTT topics.

## Features

- Monitors ChargePoint home EV chargers
- Publishes connected status (1 or 0) to MQTT
- Publishes current power output in watts to MQTT
- Configurable MQTT topics
- Automatic reconnection handling
- Docker containerized for easy deployment

## Configuration

The container is configured using environment variables:

### Required Variables

- `CHARGEPOINT_USERNAME` - Your ChargePoint account username/email
- `CHARGEPOINT_PASSWORD` - Your ChargePoint account password

### MQTT Configuration

- `MQTT_BROKER` - MQTT broker hostname (default: `localhost`)
- `MQTT_PORT` - MQTT broker port (default: `1883`)
- `MQTT_USERNAME` - MQTT username (optional)
- `MQTT_PASSWORD` - MQTT password (optional)
- `MQTT_CLIENT_ID` - MQTT client ID (default: `chargepoint-mqtt`)

### Topic Configuration

- `MQTT_TOPIC_PREFIX` - Prefix for MQTT topics (default: `chargepoint`)
- `MQTT_TOPIC_CONNECTED` - Topic for connected status (default: `chargepoint/connected`)
- `MQTT_TOPIC_POWER` - Topic for power output (default: `chargepoint/power`)

### Other Configuration

- `POLL_INTERVAL` - How often to poll ChargePoint in seconds (default: `60`)

## Usage

### Docker Run

```bash
docker run -d \
  --name chargepoint-mqtt \
  -e CHARGEPOINT_USERNAME=your_email@example.com \
  -e CHARGEPOINT_PASSWORD=your_password \
  -e MQTT_BROKER=mqtt.example.com \
  -e MQTT_USERNAME=mqtt_user \
  -e MQTT_PASSWORD=mqtt_pass \
  ghcr.io/mccahan/chargepoint-mqtt:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  chargepoint-mqtt:
    image: ghcr.io/mccahan/chargepoint-mqtt:latest
    restart: unless-stopped
    environment:
      CHARGEPOINT_USERNAME: your_email@example.com
      CHARGEPOINT_PASSWORD: your_password
      MQTT_BROKER: mqtt.example.com
      MQTT_PORT: 1883
      MQTT_USERNAME: mqtt_user
      MQTT_PASSWORD: mqtt_pass
      MQTT_TOPIC_PREFIX: chargepoint
      POLL_INTERVAL: 60
```

### Building Locally

```bash
# Clone the repository
git clone https://github.com/mccahan/chargepoint-mqtt.git
cd chargepoint-mqtt

# Build the Docker image
docker build -t chargepoint-mqtt .

# Run the container
docker run -d \
  --name chargepoint-mqtt \
  -e CHARGEPOINT_USERNAME=your_email@example.com \
  -e CHARGEPOINT_PASSWORD=your_password \
  -e MQTT_BROKER=mqtt.example.com \
  chargepoint-mqtt
```

## MQTT Topics

By default, the following topics are published:

- `chargepoint/connected` - Contains `1` if a vehicle is connected and charging/plugged in, `0` otherwise
- `chargepoint/power` - Contains the current power output in watts (e.g., `7200.0` for 7.2kW)

Both topics are published with the `retain` flag set to `true`.

## Home Assistant Integration

You can easily integrate this with Home Assistant using MQTT sensors:

```yaml
mqtt:
  sensor:
    - name: "ChargePoint Connected"
      state_topic: "chargepoint/connected"
      value_template: "{{ value }}"
      
    - name: "ChargePoint Power"
      state_topic: "chargepoint/power"
      value_template: "{{ value }}"
      unit_of_measurement: "W"
      device_class: power
```

## Dependencies

- [python-chargepoint](https://github.com/mbillow/python-chargepoint) - ChargePoint API client
- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) - MQTT client

## License

MIT
