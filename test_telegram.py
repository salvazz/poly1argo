import requests
r = requests.post(
    "https://api.telegram.org/bot8617326814:AAFJGMTv9Em8MWQ3UWZKH6GMDVXLX9sVrsU/sendMessage",
    json={"chat_id": "379974034", "text": "ARGO SISTEMA ONLINE - Tu servidor en Oracle Cloud esta activo y conectado. Los agentes te informaran aqui de cada operacion."}
)
print(r.text)
