"""
ASGI config for casino_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

# import os
# import socketio
# from django.core.asgi import get_asgi_application

# from casino_server.views import sio
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_socketio.settings')

# django_app = get_asgi_application()
# app = socketio.ASGIApp(sio)

# application = socketio.ASGIApp(sio, django_app)

import os
import socketio

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_socketio.settings')

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
application = socketio.ASGIApp(sio, get_asgi_application())
