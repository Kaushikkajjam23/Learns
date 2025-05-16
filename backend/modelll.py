import requests
import json

url = "https://ai-proxy.lab.epam.com/openai/models"
headers = {
    "Api-Key": "dial-uic4k8ruy8z34a2eswaxs6teeak"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    parsed_response = json.loads(response.text)

    with open("model_details.txt", "w") as file:
        for model in parsed_response['data']:
            try:
                file.write("=" * 50 + "\n")
                file.write(f"Model ID: {model['id']}\n")
                file.write(f"Display Name: {model.get('display_name', 'N/A')}\n")
                file.write(f"Display Version: {model.get('display_version', 'N/A')}\n")
                file.write(f"Description:\n")
                file.write(model.get('description', 'N/A') + "\n")
                file.write(f"\nFeatures:\n")
                for feature, value in model.get('features', {}).items():
                    file.write(f"  - {feature}: {value}\n")
                file.write(f"\nDescription Keywords: {', '.join(model.get('description_keywords', []))}\n")
                file.write(f"\nCapabilities:\n")
                for capability, value in model.get('capabilities', {}).items():
                    file.write(f"  - {capability}: {value}\n")
                file.write(f"\nPricing:\n")
                for unit, price in model.get('pricing', {}).items():
                    file.write(f"  - {unit}: {price}\n")
            except KeyError as e:
                file.write(f"Error occurred for model {model.get('id', 'Unknown')}: {str(e)}\n")
                continue
else:
    with open("model_details.txt", "w") as file:
        file.write(f"Request failed with status code: {response.status_code}\n")