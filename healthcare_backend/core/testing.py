from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

PASSWORD = "Str0ng!Pass99"


class BaseAPITestCase(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache

    @staticmethod
    def make_user(email="asha@example.com", name="Asha", **extra):
        return get_user_model().objects.create_user(email=email, name=name, password=PASSWORD, **extra)

    @staticmethod
    def client_for(user):
        client = APIClient()
        client.force_authenticate(user)
        return client
