import io

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import Category, CompatibilityRule, Product, ProductAttribute, ProductImage


class CatalogEditingTests(TestCase):
    def test_category_rename_preserves_links(self):
        category = Category.objects.create(name='Old category')
        product = Product.objects.create(external_id='category-test', category=category,
            payload={'cat': category.name, 'name': 'Test'})
        rule = CompatibilityRule.objects.create(name='Category rule', source_category=category.name,
            target_category=category.name, source_attribute='Socket', target_attribute='Socket', operator='equal')
        response = self.client.patch('/api/admin/categories/rename/',
            {'old_name': category.name, 'name': 'New category'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        category.refresh_from_db()
        product.refresh_from_db()
        rule.refresh_from_db()
        self.assertEqual(category.name, 'New category')
        self.assertEqual(product.category_id, category.pk)
        self.assertEqual(product.payload['cat'], 'New category')
        self.assertEqual((rule.source_category, rule.target_category), ('New category', 'New category'))

    def test_category_invalid_or_duplicate_name_is_rejected(self):
        category = Category.objects.create(name='Original category')
        Category.objects.create(name='Existing category')
        for name in ['', ' ', 'x' * 101, 'existing category']:
            response = self.client.patch('/api/admin/categories/rename/',
                {'old_name': category.name, 'name': name}, content_type='application/json')
            self.assertEqual(response.status_code, 400)
        category.refresh_from_db()
        self.assertEqual(category.name, 'Original category')

    def test_local_category_can_be_saved_and_renamed(self):
        response = self.client.patch('/api/admin/categories/rename/',
            {'old_name': 'Local demo category', 'name': 'Saved category'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(name='Saved category').exists())
        self.assertFalse(Category.objects.filter(name='Local demo category').exists())

    def test_rename_preserves_identity_and_updates_products_and_rules(self):
        attribute = ProductAttribute.objects.create(name='Test socket', values=['AM4'])
        product = Product.objects.create(external_id='test', payload={
            'name': 'CPU', 'attributes': [{'name': attribute.name, 'value': 'AM4'}],
        })
        rule = CompatibilityRule.objects.create(name='Test rule', source_category='CPU',
            target_category='Mainboard', source_attribute=attribute.name,
            target_attribute=attribute.name, operator='equal')
        response = self.client.patch(f'/api/admin/product-attributes/{attribute.pk}/',
            {'name': 'New socket', 'values': ['AM5', 'AM5']}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['attribute']['id'], str(attribute.pk))
        attribute.refresh_from_db()
        product.refresh_from_db()
        rule.refresh_from_db()
        self.assertEqual(attribute.values, ['AM5'])
        self.assertEqual(product.payload['attributes'], [{'name': 'New socket', 'value': 'AM4'}])
        self.assertEqual((rule.source_attribute, rule.target_attribute), ('New socket', 'New socket'))

    def test_duplicate_rename_does_not_change_data(self):
        attribute = ProductAttribute.objects.create(name='Original', values=[])
        ProductAttribute.objects.create(name='Existing', values=[])
        response = self.client.patch(f'/api/admin/product-attributes/{attribute.pk}/',
            {'name': 'existing', 'values': []}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        attribute.refresh_from_db()
        self.assertEqual(attribute.name, 'Original')

    def test_uploaded_image_is_stored_in_database_and_retrievable(self):
        image = io.BytesIO()
        Image.new('RGB', (2, 2), 'blue').save(image, format='PNG')
        content = image.getvalue()
        response = self.client.post('/api/admin/product-images/', {
            'file': SimpleUploadedFile('photo.png', content, content_type='image/png'),
        })
        self.assertEqual(response.status_code, 201)
        stored = ProductImage.objects.get()
        self.assertEqual(bytes(stored.content), content)
        url = response.json()['url']
        image_response = self.client.get(url)
        self.assertEqual(image_response.content, content)
        self.assertEqual(image_response['Content-Type'], 'image/png')
        # Saving a product must retain the uploaded URL through subsequent reads.
        result = self.client.put('/api/admin/products/', [{'id': 'photo-test', 'name': 'Photo test', 'img': url}], content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get('/api/admin/products/').json()['results'][0]['img'], url)

    def test_invalid_and_oversize_uploads_are_rejected(self):
        for content in [b'<svg onload="alert(1)"></svg>', b'x' * (5 * 1024 * 1024 + 1)]:
            response = self.client.post('/api/admin/product-images/', {
                'file': SimpleUploadedFile('fake.png', content, content_type='image/png'),
            })
            self.assertEqual(response.status_code, 400)
        self.assertFalse(ProductImage.objects.exists())
