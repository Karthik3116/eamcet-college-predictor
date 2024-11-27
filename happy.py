import requests
from concurrent.futures import ThreadPoolExecutor

# Define the URL
url = "https://camo.githubusercontent.com/78e3712e97e23c65ebb0270485c9b455e19d192f6ede132708aa3121b228fca9/68747470733a2f2f6b6f6d617265762e636f6d2f67687076632f3f757365726e616d653d72687974686d6a61796565266c6162656c3d50726f66696c65253230766965777326636f6c6f723d306537356236267374796c653d666c6174"

# Function to send a GET request
def send_request():
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")

# Use ThreadPoolExecutor to send requests concurrently
with ThreadPoolExecutor(max_workers=100) as executor:
    futures = [executor.submit(send_request) for _ in range(1000)]

# Wait for all threads to complete
for future in futures:
    future.result()
