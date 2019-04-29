#!/usr/bin/env python3

'''
Figshare API convenience functions.
Modified from code provided by Daniel Gavrila
Requires Python 3.6+ due to the use of f-strings.
Logging is now implemented.
'''

#import hashlib, json, os, logging, retrying
import os, logging

import requests
from requests.exceptions import HTTPError
#from retrying import retry

## Namespace

class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

## define globals

BASE_URL = 'https://api.figshare.com/v2/{endpoint}'
CHUNK_SIZE = 1048576
COLLECTION_ID = 4414307

## get token

## methods

def logthis(msg,logger=None):
    if logger:
        logger.info(msg)
    else:
        print(msg)

def raw_issue_request(method, url, data=None, binary=False, logger=None):
    if data is not None and not binary:
        data = json.dumps(data)
    response = requests.request(method, url, data=data)
    try:
        response.raise_for_status()
        try:
            data = json.loads(response.content)
        except ValueError:
            data = response.reason
    except HTTPError as error:
        if logger:
            logger.error(f'Caught an HTTPError: {error.response.status_code}')
            logger.error('Body:\n' + response.reason)
        else:
            print('Caught an HTTPError: {}'.format(error.response.status_code))
            print('Body:\n', response.reason)
        raise

    return data

def issue_request(method, endpoint, logger=None, *args, **kwargs):
    return raw_issue_request(method, BASE_URL.format(endpoint=endpoint), logger=logger, *args, **kwargs)

def get_collection_articles(collection_id=COLLECTION_ID, page=1, page_size=100, logger=None):
    endpoint = f'collections/{collection_id}/articles'
    logthis(f'Listing articles for {collection_id}.')
    result = True
    output = []
    while result:
        endpoint_curr = f'{endpoint}?page={page}&page_size={page_size}'
        result = issue_request('GET', endpoint_curr, logger=logger)
        if result:
            output += result
            page += 1
    return output

def get_article_info(article_id, logger=None):
    endpoint = f'articles/{article_id}'
    logthis(f'Getting info for article {article_id}.')
    result = issue_request('GET', endpoint, logger=logger)
    return result

