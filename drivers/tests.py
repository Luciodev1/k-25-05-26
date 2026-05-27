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

    def test_detail_view(self):
        self.client.force_login(self._create_user())
        response = self.client.get(f'/drivers/{self.driver.pk}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestDriver')

    def test_update_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post(f'/drivers/{self.driver.pk}/update/', {
            'name': 'Updated', 'phone': '+244911111111',
            'truck_plate': 'XX-00-00-XX', 'cistern_plate': 'YY-00-00-YY',
        })
        self.assertEqual(response.status_code, 302)
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.name, 'Updated')

    def test_delete_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post(f'/drivers/{self.driver.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        self.driver.refresh_from_db()
        self.assertTrue(self.driver.is_deleted)

    def test_trash_view(self):
        self.client.force_login(self._create_user())
        self.driver.delete()
        response = self.client.get('/drivers/trash/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestDriver')

    def test_restore_view(self):
        self.client.force_login(self._create_user())
        self.driver.delete()
        response = self.client.post(f'/drivers/{self.driver.pk}/restore/')
        self.assertEqual(response.status_code, 302)
        self.driver.refresh_from_db()
        self.assertFalse(self.driver.is_deleted)

    def test_hard_delete_view(self):
        self.client.force_login(self._create_user())
        self.driver.delete()
        response = self.client.post(f'/drivers/{self.driver.pk}/hard-delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Driver.all_objects.filter(pk=self.driver.pk).exists())

    def _create_user(self):
        from django.contrib.auth.models import User
        return User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')


class DriverFormTest(TestCase):
    def test_driver_form_valid(self):
        from drivers.forms import DriverForm
        form = DriverForm(data={
            'name': 'Test', 'phone': '+244911111111',
            'truck_plate': 'XX-00-00-XX', 'cistern_plate': 'YY-00-00-YY',
        })
        self.assertTrue(form.is_valid(), form.errors)

