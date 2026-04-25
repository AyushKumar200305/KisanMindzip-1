import requests

url = "http://127.0.0.1:5000/api/crop-doctor"

with open(r"C:\Users\divya\OneDrive\Pictures\Screenshots\fungal-smut-crop-disese.jpg.webp", "rb") as f:
    files = {"image": f}
    data = {"crop_name": "Wheat"}
    response = requests.post(url, files=files, data=data)
    print(response.json())