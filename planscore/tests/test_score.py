import unittest, unittest.mock, io, os, contextlib, json, gzip, itertools
from .. import score, data
import botocore.exceptions
from osgeo import ogr, gdal

should_gzip = itertools.cycle([True, False])

# Don't clutter output when running invalid data in tests
gdal.PushErrorHandler('CPLQuietErrorHandler')

def mock_s3_get_object(Bucket, Key):
    '''
    '''
    path = os.path.join(os.path.dirname(__file__), 'data', Key)
    if not os.path.exists(path):
        raise botocore.exceptions.ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
    with open(path, 'rb') as file:
        if next(should_gzip):
            return {'Body': io.BytesIO(gzip.compress(file.read())),
                'ContentEncoding': 'gzip'}
        else:
            return {'Body': io.BytesIO(file.read())}

class TestScore (unittest.TestCase):

    def test_calculate_EG_fair(self):
        ''' Efficiency gap can be correctly calculated for a fair election
        '''
        gap1 = score.calculate_EG((2, 3, 5, 6), (6, 5, 3, 2))
        self.assertAlmostEqual(gap1, 0)

        gap2 = score.calculate_EG((2, 3, 5, 6), (6, 5, 3, 2), -.1)
        self.assertAlmostEqual(gap2, .2, msg='Should see slight +blue EG with a +red vote swing')

        gap3 = score.calculate_EG((2, 3, 5, 6), (6, 5, 3, 2), .1)
        self.assertAlmostEqual(gap3, -.2, msg='Should see slight +red EG with a +blue vote swing')

        gap4 = score.calculate_EG((2, 3, 5, 6), (6, 5, 3, 2), 0)
        self.assertAlmostEqual(gap4, gap1, msg='Should see identical EG with unchanged vote swing')

    def test_calculate_EG_unfair(self):
        ''' Efficiency gap can be correctly calculated for an unfair election
        '''
        gap1 = score.calculate_EG((1, 5, 5, 5), (7, 3, 3, 3))
        self.assertAlmostEqual(gap1, -.25)

        gap2 = score.calculate_EG((1, 5, 5, 5), (7, 3, 3, 3), -.1)
        self.assertAlmostEqual(gap2, -.05, msg='Should see lesser +red EG with a +red vote swing')

        gap3 = score.calculate_EG((1, 5, 5, 5), (7, 3, 3, 3), .1)
        self.assertAlmostEqual(gap3, -.45, msg='Should see larger +red EG with a +blue vote swing')

        gap4 = score.calculate_EG((1, 5, 5, 5), (7, 3, 3, 3), 0)
        self.assertAlmostEqual(gap4, gap1, msg='Should see identical EG with unchanged vote swing')

    @unittest.mock.patch('planscore.score.calculate_EG')
    def test_calculate_gap(self, calculate_EG):
        ''' Efficiency gap can be correctly calculated for an election
        '''
        input = data.Upload(id=None, key=None,
            districts = [
                dict(totals={'Voters': 10, 'Red Votes': 2, 'Blue Votes': 6}, tile=None),
                dict(totals={'Voters': 10, 'Red Votes': 3, 'Blue Votes': 5}, tile=None),
                dict(totals={'Voters': 10, 'Red Votes': 5, 'Blue Votes': 3}, tile=None),
                dict(totals={'Voters': 10, 'Red Votes': 6, 'Blue Votes': 2}, tile=None),
                ])
        
        output = score.calculate_gaps(score.calculate_gap(input))

        self.assertEqual(output.summary['Efficiency Gap'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[0][1], ([2, 3, 5, 6], [6, 5, 3, 2]))

        self.assertEqual(output.summary['Efficiency Gap +1 Blue'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[1][1], ([2, 3, 5, 6], [6, 5, 3, 2], .01))

        self.assertEqual(output.summary['Efficiency Gap +1 Red'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[2][1], ([2, 3, 5, 6], [6, 5, 3, 2], -.01))

    @unittest.mock.patch('planscore.score.calculate_EG')
    def test_calculate_gap_ushouse(self, calculate_EG):
        ''' Efficiency gap can be correctly calculated for a U.S. House election
        '''
        input = data.Upload(id=None, key=None,
            districts = [
                dict(totals={'US House Rep Votes': 2, 'US House Dem Votes': 6}, tile=None),
                dict(totals={'US House Rep Votes': 3, 'US House Dem Votes': 5}, tile=None),
                dict(totals={'US House Rep Votes': 5, 'US House Dem Votes': 3}, tile=None),
                dict(totals={'US House Rep Votes': 6, 'US House Dem Votes': 2}, tile=None),
                ])
        
        output = score.calculate_gaps(score.calculate_gap(input))

        self.assertEqual(output.summary['US House Efficiency Gap'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[0][1], ([2, 3, 5, 6], [6, 5, 3, 2]))

        self.assertEqual(output.summary['US House Efficiency Gap +1 Dem'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[1][1], ([2, 3, 5, 6], [6, 5, 3, 2], .01))

        self.assertEqual(output.summary['US House Efficiency Gap +1 Rep'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[2][1], ([2, 3, 5, 6], [6, 5, 3, 2], -.01))

    @unittest.mock.patch('planscore.score.calculate_EG')
    def test_calculate_gap_upperhouse(self, calculate_EG):
        ''' Efficiency gap can be correctly calculated for a State upper house election
        '''
        input = data.Upload(id=None, key=None,
            districts = [
                dict(totals={'SLDU Rep Votes': 2, 'SLDU Dem Votes': 6}, tile=None),
                dict(totals={'SLDU Rep Votes': 3, 'SLDU Dem Votes': 5}, tile=None),
                dict(totals={'SLDU Rep Votes': 5, 'SLDU Dem Votes': 3}, tile=None),
                dict(totals={'SLDU Rep Votes': 6, 'SLDU Dem Votes': 2}, tile=None),
                ])
        
        output = score.calculate_gaps(score.calculate_gap(input))

        self.assertEqual(output.summary['SLDU Efficiency Gap'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[0][1], ([2, 3, 5, 6], [6, 5, 3, 2]))

        self.assertEqual(output.summary['SLDU Efficiency Gap +1 Dem'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[1][1], ([2, 3, 5, 6], [6, 5, 3, 2], .01))

        self.assertEqual(output.summary['SLDU Efficiency Gap +1 Rep'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[2][1], ([2, 3, 5, 6], [6, 5, 3, 2], -.01))

    @unittest.mock.patch('planscore.score.calculate_EG')
    def test_calculate_gap_lowerhouse(self, calculate_EG):
        ''' Efficiency gap can be correctly calculated for a State lower house election
        '''
        input = data.Upload(id=None, key=None,
            districts = [
                dict(totals={'SLDL Rep Votes': 2, 'SLDL Dem Votes': 6}, tile=None),
                dict(totals={'SLDL Rep Votes': 3, 'SLDL Dem Votes': 5}, tile=None),
                dict(totals={'SLDL Rep Votes': 5, 'SLDL Dem Votes': 3}, tile=None),
                dict(totals={'SLDL Rep Votes': 6, 'SLDL Dem Votes': 2}, tile=None),
                ])
        
        output = score.calculate_gaps(score.calculate_gap(input))

        self.assertEqual(output.summary['SLDL Efficiency Gap'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[0][1], ([2, 3, 5, 6], [6, 5, 3, 2]))

        self.assertEqual(output.summary['SLDL Efficiency Gap +1 Dem'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[1][1], ([2, 3, 5, 6], [6, 5, 3, 2], .01))

        self.assertEqual(output.summary['SLDL Efficiency Gap +1 Rep'], calculate_EG.return_value)
        self.assertEqual(calculate_EG.mock_calls[2][1], ([2, 3, 5, 6], [6, 5, 3, 2], -.01))

    @unittest.mock.patch('planscore.score.calculate_EG')
    def test_calculate_gap_sims(self, calculate_EG):
        ''' Efficiency gap can be correctly calculated using input sims.
        '''
        input = data.Upload(id=None, key=None,
            districts = [
                dict(totals={"REP000": 2, "DEM000": 6, "REP001": 1, "DEM001": 7}, tile=None),
                dict(totals={"REP000": 3, "DEM000": 5, "REP001": 5, "DEM001": 3}, tile=None),
                dict(totals={"REP000": 5, "DEM000": 3, "REP001": 5, "DEM001": 3}, tile=None),
                dict(totals={"REP000": 6, "DEM000": 2, "REP001": 5, "DEM001": 3}, tile=None),
                ])
        
        calculate_EG.return_value = 0
        output = score.calculate_gaps(score.calculate_gap(input))
        self.assertEqual(output.summary['Efficiency Gap'], calculate_EG.return_value)
        self.assertEqual(output.summary['Efficiency Gap SD'], 0)
        self.assertIn('Efficiency Gap +1 Dem', output.summary)
        self.assertIn('Efficiency Gap +1 Dem SD', output.summary)
        self.assertIn('Efficiency Gap +1 Rep', output.summary)
        self.assertIn('Efficiency Gap +1 Rep SD', output.summary)
        self.assertEqual(calculate_EG.mock_calls[0][1], ([2, 3, 5, 6], [6, 5, 3, 2], 0))
        self.assertEqual(calculate_EG.mock_calls[1][1], ([2, 3, 5, 6], [6, 5, 3, 2], .01))
        self.assertEqual(calculate_EG.mock_calls[2][1], ([2, 3, 5, 6], [6, 5, 3, 2], -.01))
        self.assertEqual(calculate_EG.mock_calls[11][1], ([1, 5, 5, 5], [7, 3, 3, 3], 0))
        self.assertEqual(calculate_EG.mock_calls[12][1], ([1, 5, 5, 5], [7, 3, 3, 3], .01))
        self.assertEqual(calculate_EG.mock_calls[13][1], ([1, 5, 5, 5], [7, 3, 3, 3], -.01))
        
        for field in ('REP000', 'DEM000', 'REP001', 'DEM001'):
            for district in output.districts:
                self.assertNotIn(field, district['totals'])

        self.assertEqual(output.districts[0]['totals']['Republican Votes'], 3/2)
        self.assertEqual(output.districts[0]['totals']['Democratic Votes'], 13/2)
        self.assertEqual(output.districts[1]['totals']['Republican Votes'], 8/2)
        self.assertEqual(output.districts[1]['totals']['Democratic Votes'], 8/2)
        self.assertEqual(output.districts[2]['totals']['Republican Votes'], 10/2)
        self.assertEqual(output.districts[2]['totals']['Democratic Votes'], 6/2)
        self.assertEqual(output.districts[3]['totals']['Republican Votes'], 11/2)
        self.assertEqual(output.districts[3]['totals']['Democratic Votes'], 5/2)

    def test_score_district(self):
        ''' District scores are correctly read from input GeoJSON
        '''
        s3, bucket = unittest.mock.Mock(), unittest.mock.Mock()
        s3.get_object.side_effect = mock_s3_get_object
        
        with open(os.path.join(os.path.dirname(__file__), 'data', 'null-plan.geojson')) as file:
            geojson = json.load(file)
        
        feature1, feature2 = geojson['features']

        geometry1 = ogr.CreateGeometryFromJson(json.dumps(feature1['geometry']))
        totals1, tiles1, _ = score.score_district(s3, bucket, geometry1, 'XX')

        geometry2 = ogr.CreateGeometryFromJson(json.dumps(feature2['geometry']))
        totals2, tiles2, _ = score.score_district(s3, bucket, geometry2, 'XX')
        
        self.assertAlmostEqual(totals1['Voters'] + totals2['Voters'], 15)
        self.assertAlmostEqual(totals1['Blue Votes'] + totals2['Blue Votes'], 6)
        self.assertAlmostEqual(totals1['Red Votes'] + totals2['Red Votes'], 6)
        self.assertEqual(tiles1, ['12/2047/2047', '12/2047/2048'])
        self.assertEqual(tiles2, ['12/2047/2047', '12/2048/2047', '12/2047/2048', '12/2048/2048'])
    
    def test_score_district_invalid_geom(self):
        ''' District scores are correctly read despite topology error.
        '''
        s3, bucket = unittest.mock.Mock(), unittest.mock.Mock()
        s3.get_object.side_effect = mock_s3_get_object
        
        with open(os.path.join(os.path.dirname(__file__), 'data', 'NC-plan-1-992.geojson')) as file:
            geojson = json.load(file)
        
        feature = geojson['features'][0]

        geometry = ogr.CreateGeometryFromJson(json.dumps(feature['geometry']))
        totals, tiles, _ = score.score_district(s3, bucket, geometry, 'NC')
        
        self.assertAlmostEqual(totals['Voters'], 621.0287544586728)
        self.assertAlmostEqual(totals['Blue Votes'], 866.9575196315632)
        self.assertAlmostEqual(totals['Red Votes'], 811.4376789272283)
        self.assertEqual(tiles, ['12/1104/1612'])
    
    def test_score_district_missing_tile(self):
        ''' District scores come up empty for an area with no tiles
        '''
        s3, bucket = unittest.mock.Mock(), unittest.mock.Mock()
        s3.get_object.side_effect = mock_s3_get_object
        
        with open(os.path.join(os.path.dirname(__file__), 'data', 'null-ranch.geojson')) as file:
            geojson = json.load(file)
        
        feature = geojson['features'][0]
        geometry = ogr.CreateGeometryFromJson(json.dumps(feature['geometry']))
        totals, tiles, _ = score.score_district(s3, bucket, geometry, 'XX')

        self.assertFalse(totals['Voters'])
        self.assertFalse(tiles)
    
    @unittest.mock.patch('planscore.score.score_district')
    def test_score_plan_geojson(self, score_district):
        ''' District plan scores can be read from a GeoJSON source
        '''
        score_district.return_value = {'Red Votes': 0, 'Blue Votes': 1}, \
            ['zxy'], 'Better score a district.\n'
        
        plan_path = os.path.join(os.path.dirname(__file__), 'data', 'null-plan.geojson')
        upload = data.Upload('id', os.path.basename(plan_path), [])
        
        scored, output = score.score_plan(None, None, upload, plan_path, None)
        self.assertIn('2 features in 1119-byte null-plan.geojson', output)
        self.assertIn('Better score a district.', output)
        self.assertEqual(scored.districts, [{'totals': {'Red Votes': 0, 'Blue Votes': 1}, 'tiles': ['zxy']}] * 2)
        self.assertEqual(scored.summary['Efficiency Gap'], -.5)
    
    @unittest.mock.patch('planscore.score.score_district')
    def test_score_plan_gpkg(self, score_district):
        ''' District plan scores can be read from a Geopackage source
        '''
        score_district.return_value = {'Red Votes': 1, 'Blue Votes': 0}, \
            ['zxy'], 'Better score a district.\n'
        
        plan_path = os.path.join(os.path.dirname(__file__), 'data', 'null-plan.gpkg')
        upload = data.Upload('id', os.path.basename(plan_path), [])
        
        scored, output = score.score_plan(None, None, upload, plan_path, None)
        self.assertIn('2 features in 40960-byte null-plan.gpkg', output)
        self.assertIn('Better score a district.', output)
        self.assertEqual(scored.districts, [{'totals': {'Red Votes': 1, 'Blue Votes': 0}, 'tiles': ['zxy']}] * 2)
        self.assertEqual(scored.summary['Efficiency Gap'], .5)
    
    @unittest.mock.patch('planscore.score.score_district')
    def test_score_plan_missing_tile(self, score_district):
        ''' District plan scores come up empty for an area with no tiles
        '''
        score_district.return_value = {'Red Votes': 0, 'Blue Votes': 0}, \
            ['zxy'], 'Better score a district.\n'
        
        plan_path = os.path.join(os.path.dirname(__file__), 'data', 'null-plan.gpkg')
        upload = data.Upload('id', os.path.basename(plan_path))
        
        scored, output = score.score_plan(None, None, upload, plan_path, None)
        self.assertFalse(scored.summary['Efficiency Gap'])
    
    def test_score_plan_bad_file_type(self):
        ''' An error is raised when an unknown plan file type is submitted
        '''
        plan_path = __file__
        upload = data.Upload('id', os.path.basename(plan_path), [])
        
        with self.assertRaises(RuntimeError) as error:
            score.score_plan(None, None, upload, plan_path, None)
    
    def test_score_plan_bad_file_content(self):
        ''' An error is raised when a bad plan file is submitted
        '''
        plan_path = os.path.join(os.path.dirname(__file__), 'data', 'bad-data.geojson')
        upload = data.Upload('id', os.path.basename(plan_path), [])
        
        with self.assertRaises(RuntimeError) as error:
            score.score_plan(None, None, upload, plan_path, None)
    
    def test_put_upload_index(self):
        ''' Upload index file is posted to S3
        '''
        s3, bucket, upload = unittest.mock.Mock(), unittest.mock.Mock(), unittest.mock.Mock()
        score.put_upload_index(s3, bucket, upload)
        
        put_call1, put_call2 = s3.put_object.mock_calls
        
        self.assertEqual(put_call1[2], dict(Bucket=bucket,
            Key=upload.index_key.return_value,
            Body=upload.to_json.return_value.encode.return_value,
            ACL='public-read', ContentType='text/json'))
        
        self.assertEqual(put_call2[2], dict(Bucket=bucket,
            Key=upload.plaintext_key.return_value,
            Body=upload.to_plaintext.return_value.encode.return_value,
            ACL='public-read', ContentType='text/plain'))

    @unittest.mock.patch('sys.stdout')
    def test_district_completeness(self, stdout):
        ''' Correct number of completed districts is found.
        '''
        upload = data.Upload('ID', 'uploads/ID/upload/file.geojson', districts=[None, None])
        
        # First time through, there's only one district noted on the server
        storage = data.Storage(unittest.mock.Mock(), 'bucket-name', 'data/XX')
        storage.s3.list_objects.return_value = {
            'Contents': [{'Key': 'uploads/ID/districts/0.json'}]}
        
        completeness = score.district_completeness(storage, upload)
        self.assertFalse(completeness.is_complete(), 'Should see accurate return from district_completeness()')

        storage.s3.list_objects.assert_called_once_with(
            Bucket='bucket-name', Prefix='uploads/ID/districts')

        # Second time through, both expected districts are there
        storage.s3 = unittest.mock.Mock()
        storage.s3.list_objects.return_value = {'Contents': [
            {'Key': 'uploads/ID/districts/0.json'}, {'Key': 'uploads/ID/districts/1.json'}]}

        completeness = score.district_completeness(storage, upload)
        self.assertTrue(completeness.is_complete(), 'Should see accurate return from district_completeness()')
    
    @unittest.mock.patch('sys.stdout')
    @unittest.mock.patch('planscore.score.calculate_gaps')
    @unittest.mock.patch('planscore.score.calculate_gap')
    @unittest.mock.patch('planscore.score.put_upload_index')
    def test_combine_district_scores(self, put_upload_index, calculate_gap, calculate_gaps, stdout):
        '''
        '''
        storage = unittest.mock.Mock()
        storage.s3.list_objects.return_value = {'Contents': [
            # Return these out of order to check sorting in score.lambda_handler()
            {'Key': 'uploads/sample-plan/districts/1.json'},
            {'Key': 'uploads/sample-plan/districts/0.json'}
            ]}
        
        storage.s3.get_object.side_effect = mock_s3_get_object

        return
        
        s3.list_objects.assert_called_once_with(
            Bucket='bucket-name', Prefix='uploads/sample-plan/districts')
        
        self.assertEqual(len(s3.get_object.mock_calls), 2, 'Should have asked for each district in turn')
        
        input_upload = calculate_gap.mock_calls[0][1][0]
        self.assertEqual(input_upload.id, 'sample-plan')
        self.assertEqual(len(input_upload.districts), 2)
        self.assertIn('totals', input_upload.districts[0])
        self.assertIn('totals', input_upload.districts[1])
        self.assertEqual(input_upload.districts[0]['geometry_key'], 'uploads/sample-plan/geometries/0.wkt')
        self.assertEqual(input_upload.districts[1]['geometry_key'], 'uploads/sample-plan/geometries/1.wkt')
        
        interim_upload = calculate_gap.return_value
        calculate_gaps.assert_called_once_with(interim_upload)
        
        output_upload = calculate_gaps.return_value
        put_upload_index.assert_called_once_with(s3, 'bucket-name', output_upload)
    
    @unittest.mock.patch('sys.stdout')
    @unittest.mock.patch('time.sleep')
    @unittest.mock.patch('boto3.client')
    @unittest.mock.patch('planscore.score.combine_district_scores')
    @unittest.mock.patch('planscore.score.district_completeness')
    def test_lambda_handler_complete(self, district_completeness, combine_district_scores, boto3_client, time_sleep, stdout):
        '''
        '''
        district_completeness.return_value = data.Progress(2, 2)

        score.lambda_handler({'bucket': 'bucket-name', 'id': 'sample-plan',
            'key': 'uploads/sample-plan/upload/file.geojson'}, None)
        
        self.assertEqual(len(combine_district_scores.mock_calls), 1)
        self.assertEqual(combine_district_scores.mock_calls[0][1][1].id, 'sample-plan')
        self.assertEqual(len(boto3_client.return_value.invoke.mock_calls), 0)
    
    @unittest.mock.patch('sys.stdout')
    @unittest.mock.patch('time.sleep')
    @unittest.mock.patch('boto3.client')
    @unittest.mock.patch('planscore.score.combine_district_scores')
    @unittest.mock.patch('planscore.score.put_upload_index')
    @unittest.mock.patch('planscore.score.district_completeness')
    def test_lambda_handler_outoftime(self, district_completeness, put_upload_index, combine_district_scores, boto3_client, time_sleep, stdout):
        '''
        '''
        context = unittest.mock.Mock()
        context.get_remaining_time_in_millis.return_value = 0
        district_completeness.return_value = data.Progress(1, 2)
        
        event = {'bucket': 'bucket-name', 'id': 'sample-plan',
            'prefix': 'XX', 'key': 'uploads/sample-plan/upload/file.geojson'}

        score.lambda_handler(event, context)
        
        self.assertEqual(len(combine_district_scores.mock_calls), 0)
        self.assertEqual(len(boto3_client.return_value.invoke.mock_calls), 1)
        self.assertEqual(len(put_upload_index.mock_calls), 1)

        kwargs = boto3_client.return_value.invoke.mock_calls[0][2]
        self.assertEqual(kwargs['FunctionName'], score.FUNCTION_NAME)
        self.assertEqual(kwargs['InvocationType'], 'Event')
        self.assertIn(b'"id": "sample-plan"', kwargs['Payload'])
        self.assertIn(b'"progress": [1, 2]', kwargs['Payload'])
        self.assertIn(event['bucket'].encode('utf8'), kwargs['Payload'])
        self.assertIn(event['prefix'].encode('utf8'), kwargs['Payload'])
    
    @unittest.mock.patch('sys.stdout')
    @unittest.mock.patch('boto3.client')
    @unittest.mock.patch('planscore.score.put_upload_index')
    @unittest.mock.patch('planscore.score.district_completeness')
    def test_lambda_handler_overdue(self, district_completeness, put_upload_index, boto3_client, stdout):
        '''
        '''
        context = unittest.mock.Mock()
        context.get_remaining_time_in_millis.return_value = 0
        district_completeness.return_value = data.Progress(1, 2)
        
        event = {'bucket': 'bucket-name', 'id': 'sample-plan',
            'prefix': 'XX', 'key': 'uploads/sample-plan/upload/file.geojson',
            'start_time': 1}

        with self.assertRaises(RuntimeError) as _:
            score.lambda_handler(event, context)

        self.assertEqual(len(put_upload_index.mock_calls), 1)
