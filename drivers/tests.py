from django.test import TestCase
from .models import Driver


class DriverModelTest(TestCase):
    def test_create_driver(self):
        driver = Driver.objects.create(
            name='TestDriver',
            phone='+244912345678',
            truck_plate='LD-12-34-AB',
            cistern_plate='LD-56-78-CD',
        )
        self.assertEqual(str(driver), 'TestDriver (LD-12-34-AB)')

    def test_driver_ordering(self):
        Driver.objects.create(name='Zebra', phone='1', truck_plate='A', cistern_plate='B')
        Driver.objects.create(name='Alpha', phone='2', truck_plate='C', cistern_plate='D')
        drivers = list(Driver.objects.values_list('name', flat=True))
        self.assertEqual(drivers, ['Alpha', 'Zebra'])


class DriverViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.driver = Driver.objects.create(
            name='TestDriver',
            phone='+244912345678',
            truck_plate='LD-12-34-AB',
            cistern_plate='LD-56-78-CD',
        )

    def test_list_requires_login(self):
        response = self.client.get('/drivers/list/')
        self.assertEqual(response.status_code, 302)

    def test_list_view(self):
        self.client.force_login(self._create_user())
        response = self.client.get('/drivers/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestDriver')

    def test_create_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post('/drivers/create/', {
            'name': 'NewDriver',
            'phone': '+244911111111',
            'truck_plate': 'XX-00-00-XX',
            'cistern_plate': 'YY-00-00-YY',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Driver.objects.filter(name='NewDriver').exists())

    def _create_user(self):
        from django.contrib.auth.models import User
        return User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')

