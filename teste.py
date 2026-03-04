import requests

url = "http://127.0.0.1:5000/api/jobs"

headers = {
    "accept": "*/*",
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,cs;q=0.6",
    "content-type": "application/json",
    "sec-ch-ua": "\"Not:A-Brand\";v=\"99\", \"Google Chrome\";v=\"145\", \"Chromium\";v=\"145\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Linux\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
}

payload = {
    "vortal_user": "josealves@nordhigiene.pt",
    "vortal_password": "Nord#2026***1",
    "acingov_user": "josealves@nordhigiene.pt",
    "acingov_password": "M18122007a",
    "date_from": "2026-03-03",
    "date_to": "2026-03-03",
    "headless": False,
    "use_word_boundaries": True
}

response = requests.post(
    url,
    headers=headers,
    json=payload  # já serializa para JSON automaticamente
)

print("Status:", response.status_code)
print("Response:", response.text)
