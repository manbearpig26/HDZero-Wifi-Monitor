import subprocess
import time
from flask import Flask, render_template_string, jsonify, request
import threading

app = Flask(__name__)

# Replace with your HDZero Wi-Fi SSID
WIFI_SSID = "HDZero"

# Global variables to store connection status and stats
connection_status = "No Connection - Searching"
status_color = "#FF0000"  # Red for not connected
stats = {
    "Signal Strength": "N/A",
    "Receive Rate": "N/A",
    "Transmit Rate": "N/A",
    "Channel": "N/A"
}

def check_wifi_connection(ssid):
    """Check if the system is connected to the specified Wi-Fi SSID."""
    try:
        result = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True)
        if ssid in result.stdout:
            return True, result.stdout
        return False, result.stdout
    except Exception as e:
        print(f"Error checking Wi-Fi connection: {e}")
        return False, ""

def reconnect_to_wifi(ssid):
    """Attempt to disconnect and reconnect to the specified Wi-Fi SSID."""
    try:
        print(f"Attempting to disconnect from {ssid}...")
        # Disconnect from the current Wi-Fi
        disconnect_result = subprocess.run(["netsh", "wlan", "disconnect"], capture_output=True, text=True)
        if disconnect_result.returncode != 0:
            print(f"Failed to disconnect: {disconnect_result.stderr}")
            return False

        print(f"Disconnected from {ssid}.")
        time.sleep(2)  # Wait for the interface to fully disconnect

        print(f"Attempting to reconnect to {ssid}...")
        # Reconnect to the specified Wi-Fi
        connect_result = subprocess.run(["netsh", "wlan", "connect", f"name={ssid}"], capture_output=True, text=True)
        if connect_result.returncode != 0:
            print(f"Failed to reconnect: {connect_result.stderr}")
            return False

        print(f"Reconnected to {ssid}.")
        return True
    except Exception as e:
        print(f"Error reconnecting to Wi-Fi: {e}")
        return False

def parse_network_stats(output):
    """Extract and return network statistics from the netsh output."""
    stats = {}
    for line in output.splitlines():
        if "Signal" in line:
            stats["Signal Strength"] = line.split(":")[1].strip()
        elif "Receive rate" in line:
            stats["Receive Rate"] = line.split(":")[1].strip()
        elif "Transmit rate" in line:
            stats["Transmit Rate"] = line.split(":")[1].strip()
        elif "Channel" in line:
            stats["Channel"] = line.split(":")[1].strip()
    return stats

def monitor_wifi():
    """Continuously monitor the Wi-Fi connection and attempt to reconnect if lost."""
    global connection_status, status_color, stats
    while True:
        try:
            connected, output = check_wifi_connection(WIFI_SSID)
            if not connected:
                connection_status = "No Connection - Searching"
                status_color = "#FF0000"  # Red for not connected
                reconnect_to_wifi(WIFI_SSID)
                connected, output = check_wifi_connection(WIFI_SSID)
                if connected:
                    connection_status = "Connected"
                    status_color = "#00FF00"  # Green for connected
            else:
                connection_status = "Connected"
                status_color = "#00FF00"  # Green for connected
                stats = parse_network_stats(output)
        except Exception as e:
            print(f"Error in monitor_wifi: {e}")

        time.sleep(1)  # Check every second

@app.route("/")
def index():
    # Render the stats as an HTML page with OBS-themed styling
    html = """
    <html>
        <head>
            <title>Wi-Fi Monitor</title>
            <style>
                body {
                    background-color: #2B2B2B; /* OBS dark background */
                    color: #FFFFFF; /* White text */
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                }
                h1 {
                    color: #1E90FF; /* OBS blue for headings */
                    font-size: 24px;
                    margin-bottom: 20px;
                }
                .stats-container {
                    background-color: #3C3C3C; /* Slightly lighter background for stats */
                    padding: 15px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
                }
                .stat-item {
                    margin-bottom: 10px;
                    font-size: 18px;
                }
                .signal-strength {
                    color: #FFD700; /* Gold color for signal strength */
                    font-weight: bold;
                }
                .connection-status {
                    display: flex;
                    align-items: center;
                    margin-bottom: 15px;
                }
                .status-indicator {
                    width: 15px;
                    height: 15px;
                    border-radius: 50%;
                    margin-right: 10px;
                }
                .reset-button {
                    background-color: #1E90FF; /* OBS blue */
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                }
                .reset-button:hover {
                    background-color: #0077CC; /* Darker blue on hover */
                }
            </style>
            <script>
                function updateStatus() {
                    fetch("/status")
                        .then(response => response.json())
                        .then(data => {
                            // Update connection status
                            document.getElementById("connection-status").innerText = data.connection_status;
                            document.getElementById("status-indicator").style.backgroundColor = data.status_color;

                            // Update network stats
                            document.getElementById("signal-strength").innerText = data.signal_strength;
                            document.getElementById("receive-rate").innerText = data.receive_rate;
                            document.getElementById("transmit-rate").innerText = data.transmit_rate;
                            document.getElementById("channel").innerText = data.channel;
                        })
                        .catch(error => console.error("Error fetching status:", error));
                }

                function resetWifi() {
                    fetch("/reset_wifi", { method: "POST" })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert("Wi-Fi reset successful!");
                            } else {
                                alert("Failed to reset Wi-Fi. Check logs for details.");
                            }
                        })
                        .catch(error => {
                            console.error("Error resetting Wi-Fi:", error);
                            alert("An error occurred while resetting Wi-Fi.");
                        });
                }

                // Update the status every second
                setInterval(updateStatus, 1000);
                updateStatus(); // Initial call to update status immediately
            </script>
        </head>
        <body>
            <h1>Wi-Fi Monitor</h1>
            <div class="stats-container">
                <div class="connection-status">
                    <div id="status-indicator" class="status-indicator" style="background-color: {{ status_color }};"></div>
                    <div><strong>Status:</strong> <span id="connection-status">{{ connection_status }}</span></div>
                </div>
                <div class="stat-item"><strong>Connected to:</strong> {{ ssid }}</div>
                <div class="stat-item signal-strength"><strong>Signal Strength:</strong> <span id="signal-strength">{{ stats["Signal Strength"] }}</span></div>
                <div class="stat-item"><strong>Receive Rate:</strong> <span id="receive-rate">{{ stats["Receive Rate"] }}</span></div>
                <div class="stat-item"><strong>Transmit Rate:</strong> <span id="transmit-rate">{{ stats["Transmit Rate"] }}</span></div>
                <div class="stat-item"><strong>Channel:</strong> <span id="channel">{{ stats["Channel"] }}</span></div>
                <button class="reset-button" onclick="resetWifi()">Reset Wi-Fi</button>
            </div>
        </body>
    </html>
    """
    return render_template_string(html, ssid=WIFI_SSID, stats=stats, connection_status=connection_status, status_color=status_color)

@app.route("/status")
def get_status():
    """Endpoint to fetch the current connection status and stats."""
    return jsonify({
        "connection_status": connection_status,
        "status_color": status_color,
        "signal_strength": stats["Signal Strength"],
        "receive_rate": stats["Receive Rate"],
        "transmit_rate": stats["Transmit Rate"],
        "channel": stats["Channel"]
    })

@app.route("/reset_wifi", methods=["POST"])
def reset_wifi():
    """Endpoint to reset the Wi-Fi connection."""
    try:
        success = reconnect_to_wifi(WIFI_SSID)
        return jsonify({"success": success})
    except Exception as e:
        print(f"Error resetting Wi-Fi: {e}")
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    # Start the Wi-Fi monitoring thread
    monitor_thread = threading.Thread(target=monitor_wifi)
    monitor_thread.daemon = True
    monitor_thread.start()

    # Start the Flask web server
    app.run(host="0.0.0.0", port=5000)