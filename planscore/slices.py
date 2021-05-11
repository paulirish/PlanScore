import os, json, io, gzip, posixpath, functools, collections, time
import boto3, botocore.exceptions
from . import constants, data

FUNCTION_NAME = os.environ.get('FUNC_NAME_RUN_SLICE') or 'PlanScore-RunSlice'

def load_upload_assignments(storage, upload):
    ''' Get dictionary of assignments for an upload.
    '''
    assignments = {}
    
    assign_prefix = posixpath.dirname(data.UPLOAD_ASSIGNMENTS_KEY).format(id=upload.id)
    response = storage.s3.list_objects(Bucket=storage.bucket, Prefix=f'{assign_prefix}/')

    assignment_keys = [object['Key'] for object in response['Contents']]
    
    for assignment_key in assignment_keys:
        object = storage.s3.get_object(Bucket=storage.bucket, Key=assignment_key)

        if object.get('ContentEncoding') == 'gzip':
            object['Body'] = io.BytesIO(gzip.decompress(object['Body'].read()))
    
        district_list = object['Body'].read().decode('utf8').split('\n')
        assignments[assignment_key] = set(district_list)
    
    return assignments

def load_slice_precincts(storage, slice_zxy):
    ''' Get list of properties for a specific slice.
    '''
    try:
        # Search for slice GeoJSON inside the storage prefix
        print('storage.s3.get_object():', dict(Bucket=storage.bucket,
            Key='{}/slices/{}.json'.format(storage.prefix, slice_zxy)))
        object = storage.s3.get_object(Bucket=storage.bucket,
            Key='{}/slices/{}.json'.format(storage.prefix, slice_zxy))
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'NoSuchKey':
            return []
        raise

    if object.get('ContentEncoding') == 'gzip':
        object['Body'] = io.BytesIO(gzip.decompress(object['Body'].read()))
    
    properties_list = json.load(object['Body'])
    return properties_list

def get_slice_geoid(model_key_prefix, slice_key):
    '''
    '''
    slice_geoid, _ = posixpath.splitext(posixpath.relpath(slice_key, model_key_prefix))
    
    assert slice_geoid.startswith('slices/'), slice_geoid
    return slice_geoid[7:]

def score_district(district_set, precincts, slice_set):
    ''' Return weighted precinct totals for a district over a tile.
    '''
    totals = collections.defaultdict(int)
    partial_district_set = district_set & slice_set
    
    if not partial_district_set:
        return totals

    for precinct_feat in precincts:
        subtotals = score_precinct(partial_district_set, precinct_feat, slice_set)
        for (name, value) in subtotals.items():
            totals[name] = round(value + totals[name], constants.ROUND_COUNT)

    return totals

def score_precinct():
    pass

def lambda_handler(event, context):
    '''
    '''
    start_time = time.time()
    s3 = boto3.client('s3')
    storage = data.Storage.from_event(event['storage'], s3)
    upload = data.Upload.from_dict(event['upload'])
    
    print('slices.lambda_handler():', json.dumps(event))

    try:
        slice_geoid = get_slice_geoid(upload.model.key_prefix, event['slice_key'])
        output_key = data.UPLOAD_SLICES_KEY.format(id=upload.id, geoid=slice_geoid)
        slice_set = slice_assignment(slice_geoid)

        totals = {}
        precincts = load_slice_precincts(storage, slice_geoid)
        assignments = load_upload_assignments(storage, upload)
    
        for (assignment_key, district_set) in assignments.items():
            totals[assignment_key] = score_district(district_set, precincts, slice_set)
    except Exception as err:
        print('Exception:', err)
        totals = str(err)
        feature_count = None
    else:
        feature_count = len(precincts)

    timing = dict(
        start_time=round(start_time, 3),
        elapsed_time=round(time.time() - start_time, 3),
        features=feature_count,
    )
    
    print('s3.put_object():', dict(Bucket=storage.bucket, Key=output_key,
        Body=dict(event, totals=totals, timing=timing),
        ContentType='text/plain', ACL='public-read'))

    s3.put_object(Bucket=storage.bucket, Key=output_key,
        Body=json.dumps(dict(event, totals=totals, timing=timing)).encode('utf8'),
        ContentType='text/plain', ACL='public-read')
