import unittest, unittest.mock, os
from .. import callback, data, districts, constants

class TestCallback (unittest.TestCase):

    def setUp(self):
        self.prev_secret, constants.SECRET = constants.SECRET, 'fake-secret'
        self.prev_website, constants.WEBSITE_BASE = constants.WEBSITE_BASE, 'https://example.com/'
        self.prev_s3_url, constants.S3_ENDPOINT_URL = constants.S3_ENDPOINT_URL, None
        self.prev_lam_url, constants.LAMBDA_ENDPOINT_URL = constants.LAMBDA_ENDPOINT_URL, None
    
    def tearDown(self):
        constants.SECRET = self.prev_secret
        constants.WEBSITE_BASE = self.prev_website
        constants.S3_ENDPOINT_URL = self.prev_s3_url
        constants.LAMBDA_ENDPOINT_URL = self.prev_lam_url

    @unittest.mock.patch('planscore.callback.create_upload')
    @unittest.mock.patch('boto3.client')
    def test_lambda_handler(self, boto3_client, create_upload):
        ''' Lambda event triggers the right call to create_upload()
        '''
        query = {'id': 'id.k0_XwbOLGLUdv241zsPluNc3HYs', 'bucket': 'planscore',
            'key': data.UPLOAD_PREFIX.format(id='id') + 'file.geojson'}

        os.environ.update(AWS_ACCESS_KEY_ID='fake-key', AWS_SECRET_ACCESS_KEY='fake-secret')

        create_upload.return_value = data.Upload(query['id'], query['key'])
        response = callback.lambda_handler({'queryStringParameters': query}, None)
        
        self.assertEqual(response['statusCode'], '302')
        self.assertEqual(response['headers']['Location'], 'https://example.com/plan.html?id')
        
        self.assertEqual(create_upload.mock_calls[0][1][1:],
            (query['bucket'], query['key'], 'id'))
        
        lambda_dict = boto3_client.return_value.invoke.mock_calls[0][2]
        
        self.assertEqual(lambda_dict['FunctionName'], 'PlanScore-AfterUpload')
        self.assertEqual(lambda_dict['InvocationType'], 'Event')
        self.assertIn(b'"id": "id.k0_XwbOLGLUdv241zsPluNc3HYs"', lambda_dict['Payload'])
        self.assertIn(b'"key": "uploads/id/upload/file.geojson"', lambda_dict['Payload'])
