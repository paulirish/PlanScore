#!/usr/bin/env python
import sys, boto3
import botocore.exceptions

def describe_api(api, api_name):
    '''
    '''
    try:
        print('    * get API', api_name, file=sys.stderr)
        rest_api = [item for item in api.get_rest_apis()['items']
            if item['name'] == api_name][0]
    except:
        print('    * did not find API', api_name, file=sys.stderr)
        raise
    else:
        rest_api_id = rest_api['id']
    
    return rest_api_id

def deploy_api(api, rest_api_id):
    print('    * create deployment', rest_api_id, 'test', file=sys.stderr)
    api.create_deployment(stageName='test', restApiId=rest_api_id)

if __name__ == '__main__':
    api = boto3.client('apigateway', region_name='us-east-1')
    rest_api_id = describe_api(api, 'PlanScore')
    deploy_api(api, rest_api_id)
