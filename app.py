'''
Rana Karmakar
AI Engineer - YogiFi
'''

import asyncio
import json
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from bleak import BleakScanner, BleakClient
from io import BytesIO
import warnings
import re, requests

warnings.filterwarnings("ignore")

st.set_page_config(page_title=None, page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)

ROWS = 60
COLS = 22

async def discover_devices():
    try:
        devices = await BleakScanner.discover()
        return devices
    except Exception as e:
        st.error(f"Error discovering devices: {e}")
        return []

async def connect_to_device(device_address):
    try:
        client = BleakClient(device_address)
        await client.connect()
        return client
    except Exception as e:
        st.error(f"Failed to connect to {device_address}. Error: {e}")
        return None

async def disconnect_from_device(client):
    try:
        await client.disconnect()
        st.info("Disconnected from the device.")
    except Exception as e:
        st.error(f"Error disconnecting from the device: {e}")

async def discover_services(client):
    try:
        await client.is_connected()
        services = client.services
        return services
    except Exception as e:
        st.error(f"Failed to discover services. Error: {e}")
        return []

async def send_and_receive_data_with_notifications(client, json_data):
    service_uuid = "0000180f-0000-1000-8000-00805f9b34fb"
    write_char_uuid = "0000abf1-0000-1000-8000-00805f9b34fb"
    read_char_uuid = "0000abf2-0000-1000-8000-00805f9b34fb"
    try:
        await client.start_notify(read_char_uuid, notification_handler)
        json_dumb = json.dumps(json_data).encode("utf-8")
        await client.write_gatt_char(write_char_uuid, json_dumb)
        await asyncio.sleep(2)
        await client.stop_notify(read_char_uuid)
    except Exception as e:
        st.error(f"Error during communication: {e}")

def extract_integers(input_string):
    return [int(match) for match in re.findall(r'\d+', input_string)]

def make_rest_api_call(chunk_data):
    api_url = "https://127.0.0.1:8000/v1/detect/correct/asana"  # Replace with your actual API endpoint
    headers = {"Content-Type": "application/json"}

    # Construct the API request payload
    api_request_data = {
        "asanaId": "YFA0001",
        "programId": "YSQALL2",
        "data": chunk_data,
        "preCorFlag": False,
        "posCorFlag": True,
        "reverseFlag": 0,
        "cvMatFlag": "True",
        "userId": "6517b3edbffc8cb4f2381f4f",
        "matId": "YG2082001A01I00367",
        "km": {
            "R0": {"obj": []},
            "R1": {"obj": []},
            "_id": "6517ce905f32288f04dd2764",
            "status": "Yes",
            "n_rows_cons": 59,
            "n_clusters": 3,
            "ori": 1
        },
        "timestamp": "30-00-2023-GMT+530-01-01-17-PM",
        "difficulty": "easy",
        "gen": 2,
        "debug": False,
        "cvc_f": False
    }

    try:
        response = requests.post(api_url, data=json.dumps(api_request_data), headers=headers, verify=False)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        response_data = response.json()
        return response_data
    except requests.exceptions.RequestException as e:
        st.error(f"Error making REST API call: {e}")
        return None

def notification_handler(sender: int, data: bytearray):
    global accumulated_data
    # print(data)
    try:
        data = data.decode('utf-8')
        if 'accumulated_data' not in globals():
            accumulated_data = []
        accumulated_data.extend(extract_integers(data))
        if len(accumulated_data) >= ROWS * COLS:
            chunk = accumulated_data[:ROWS * COLS]
            # response_data = make_rest_api_call(chunk)
            # Find the top 10 highest data points
            count_greater_than_135 = sum(x > 135 for x in chunk)
            count_greater_than_80 = sum(x > 135 for x in chunk)
            top_10_highest = sorted(chunk, reverse=True)[:10]
            # Print the results
            col1, col2 = st.columns(2)
            with col2:
                st.subheader("Number of data points > 135")
                st.markdown(count_greater_than_135)
                st.subheader("Number of data points > 80")
                st.text(count_greater_than_80)
                st.subheader("Top 10 highest data points:")
                st.text(top_10_highest)
                st.subheader("Raw Data")
                with st.container(height=300):
                    st.markdown(chunk)
            # st.text(chunk)
            accumulated_data = None
            data_matrix = np.array(chunk).reshape(ROWS, COLS)
            with col1:
                with st.container(height=700):
                    visualize_heatmap(data_matrix)
                
                heatmap_buffer = download_heatmap_button(data_matrix)
                st.download_button(
                        label="Download Heatmap",
                        data=heatmap_buffer,
                        file_name="heatmap.png",
                        key="download_heatmap_button"
                    )
    except RuntimeError as e:
        pass
    except Exception as e:
        pass
    
        
def download_heatmap_button(data_matrix):
    try:
        buffer = BytesIO()
        fig, ax = plt.subplots(figsize=(1, 1))
        cax = ax.imshow(data_matrix, cmap="viridis", extent=[0, COLS, 0, ROWS])
        plt.axis("off")
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Error creating heatmap image: {e}")
        return None

def visualize_heatmap(data_matrix):
    fig, ax = plt.subplots(figsize=(3, 1))
    cax = ax.imshow(data_matrix, cmap="viridis", extent=[0, COLS, 0, ROWS])
    # plt.colorbar(cax)
    plt.axis("off")
    # ax.set_title("Heatmap")
    st.pyplot(fig)

async def main():
    st.title("YogiFi Mat Data Explorer")

    # Discover available devices
    col1, col2 = st.columns(2)
    with col2:
        if st.button("Search Device"):
            devices = await discover_devices()
            st.write("Available Devices:")
            with st.container(height=250):
                for device in devices:
                    if device.name == None:
                        pass
                    st.write(f"- {device.name} ({device.address})")
                    
    with col1:
        device_address_input = st.text_input("Enter BLE device address:")
        try:
            if st.button("Connect"):
                client = await connect_to_device(device_address_input)
            
                if client:
                    st.success("Connected to the device.")
                    services = await discover_services(client)
                
                    json_data = {"mode": "Mat_Data", "status": True}
                    await send_and_receive_data_with_notifications(client, json_data)

                    # Allow the user to disconnect manually
                    if st.button("Disconnect"):
                        await disconnect_from_device(client)
                else:
                    st.warning("Please enter a valid YogiFi Mat address.")
        except Exception as e:
            st.error("Can't connect", e)
            
        
    
    

if __name__ == "__main__":
    asyncio.run(main())
