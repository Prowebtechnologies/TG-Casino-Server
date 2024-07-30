"""
WSGI config for casino_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import socketio

from django.core.wsgi import get_wsgi_application
from casino_server.views import sio
import eventlet.wsgi

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'casino_backend.settings')

django_app = get_wsgi_application()
application = socketio.WSGIApp(sio, django_app)

eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 8000)), application, debug=True)
