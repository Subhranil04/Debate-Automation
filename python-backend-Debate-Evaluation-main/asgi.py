from asgiref.wsgi import WsgiToAsgi

from app import create_app

# Create the Flask (WSGI) app and adapt it to ASGI so Uvicorn can serve it.
flask_app = create_app()
app = WsgiToAsgi(flask_app)
