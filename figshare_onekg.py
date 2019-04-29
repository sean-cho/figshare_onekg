#!/usr/bin/env python3

'''
Queries 1000 Genome gVCFs collection on figshare and
download files if specified.
'''

import pickle, os, sys, argparse, json, math
import logging
from logging import FileHandler, StreamHandler
import requests, shutil, hashlib
from tqdm import tqdm
from figshare_api import *

__VERSION = '0.10.2'

def get_args():
    parser = argparse.ArgumentParser(description='Query and download 1000 Genomes gVCFs from figshare collection.')
    parser.add_argument('-d', '--dir', default='.', help='Download directory. [.]')
    parser.add_argument('-s', '--sex', action='append', help='Applied as AND with other filters')
    parser.add_argument('-p', '--population', action='append', help='Population filter, will be applied as OR with superpopulation but AND with sex.')
    parser.add_argument('-n', '--number', type=int, help='Maximum number of files to download. Downloads the first "n" files, sorted alphabetically. Default downloads all.')
    parser.add_argument('-sp', '--superpopulation', action='append', help='Superpopulation filter. Like population.')
    parser.add_argument('-nd', '--no-download', action='store_true', help='Instead of downloading files, returns a JSON containing matching sample information to stdout.')
    parser.add_argument('-nc', '--no-cache', action='store_true', help='Do not cache file information or do not use existing cache. By default, a pickle is generated at ~/.figshare/onekg_dict.pickle for quick search.')
    parser.add_argument('-l', '--log', type=str, help='Log file. [None]')
    parser.add_argument('-v', '--version', action='store_true', help='Return the version of the script.')
    return parser.parse_args()

def create_logger(logname, logfile, loglevel='INFO'):
    '''Logger'''
    # formatter = logging.Formatter('%(filename)s::%(funcName)s [%(asctime)s] [%(levelname)s]: %(message)s',
    formatter = logging.Formatter('%(filename)s: [%(asctime)s] [%(levelname)s]: %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p')
    handler = FileHandler(logfile)
    handler.setFormatter(formatter)
    streamer = StreamHandler()
    streamer.setFormatter(formatter)
    logger = logging.getLogger(logname)
    logger.setLevel(loglevel)
    logger.addHandler(handler)
    logger.addHandler(streamer)
    return logger

def terminate_logger(logger):
    '''Safely terminate logger'''
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)

def logthis(String, logger=None):
    if logger:
        logger.info(String)
    else:
        printerr(String)

def fmt_size(Size):
    for pf in ['','K','M','G','T','P']:
        if abs(Size) < 1024:
            return '%3.1f%sB' % (Size, pf)
        Size /= 1024.0

def get_metadata(logger=None):
    all_articles = get_collection_articles()
    all_articles_info = [get_article_info(x['id']) for x in all_articles]
    logthis('Downloading metadata from figshare website.', logger=logger)
    counter = 0
    onekg_dict = {}
    for article in all_articles_info:
        counter += 1
        print(counter)
        # sample_id, population, superpopulation, sex, filetype = [x.split(':')[1] for x in article['tags']]
        tags = {x.split(':')[0]:x.split(':')[1] for x in article['tags']}
        fs_id = article['id']
        filedata = article['files'][0]
        entry = {
            'sample_id': tags['sample_id'],
            'population': tags['population'],
            'superpopulation': tags['superpopulation'],
            'sex': tags['sex'],
            'md5': filedata['computed_md5'],
            'url': filedata['download_url'],
            'size': filedata['size'],
            'filename': filedata['name']
        }
        onekg_dict[tags['sample_id']] = entry
    return onekg_dict

def printerr(String, *args, **kwargs):
    print(String, file=sys.stderr, *args, **kwargs)

def validate_file(file_path, hash):
    '''
    Validates a file against an MD5 hash value

    :param file_path: path to the file for hash validation
    :type file_path:  string
    :param hash:      expected hash value of the file
    :type hash:       string -- MD5 hash value
    '''
    m = hashlib.md5()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(1024 * 1024) # 1MB
            if not chunk:
                break
            m.update(chunk)
    return m.hexdigest() == hash

def download(url, file_path, hash=None, timeout=10):
    '''
    Changed logging. Added progress bar.
    Modified from:
    Source: https://gist.github.com/idolpx/921fc79368903d3a90800ef979abb787
    Credit: idolpx
    Performs a HTTP(S) download that can be restarted if prematurely terminated.
    The HTTP server must support byte ranges.

    :param file_path: the path to the file to write to disk
    :type file_path:  string
    :param hash: hash value for file validation
    :type hash:  string (MD5 hash value)
    '''
     # don't download if the file exists
    if os.path.exists(file_path):
        return
    block_size = 1024 * 1024 # 1MB
    tmp_file_path = file_path + '.part'
    first_byte = os.path.getsize(tmp_file_path) if os.path.exists(tmp_file_path) else 0
    file_mode = 'ab' if first_byte else 'wb'
    logthis('Starting download at %.1fMB' % (first_byte / 1048576))
    file_size = -1
    try:
        file_size = int(requests.head(url).headers['Content-Length'])
        logthis('File size is %s' % fmt_size(file_size))
        headers = {"Range": "bytes=%s-" % first_byte}
        r = requests.get(url, headers=headers, stream=True)
        with open(tmp_file_path, file_mode) as f:
            for chunk in tqdm(r.iter_content(chunk_size=block_size), initial=first_byte/block_size, total=math.ceil(file_size//block_size), unit='MB', unit_scale=True):
            #for chunk in r.iter_content(chunk_size=block_size):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
    except IOError as e:
        logthis('IO Error - %s' % e)
    finally:
        # rename the temp download file to the correct name if fully downloaded
        #print(file_size)
        #print(os.path.getsize(tmp_file_path))
        if file_size == os.path.getsize(tmp_file_path):
            # if there's a hash value, validate the file
            if hash and not validate_file(tmp_file_path, hash):
                raise Exception('Error validating the file against its MD5 hash')
            #print(tmp_file_path, file_path)
            shutil.move(tmp_file_path, file_path)
        elif file_size == -1:
            raise Exception('Error getting Content-Length from server: %s' % url)

def main(args):
    if args.version:
        print(f'Version: {__VERSION}')
        return 0

    ## set up logging
    if args.log:
        logger = create_logger('onekg_download', args.log)
    else:
        logger = None

    ## set up queries
    if args.sex:
        q_sex = f'entry["sex"] in {args.sex}'
    else:
        q_sex = True
    if args.population:
        q_population = f'entry["population"] in {args.population}'
        if args.superpopulation:
            q_population = f'{q_population} or entry["superpopulation"] in {args.superpopulation}'
    elif args.superpopulation:
        q_population = f'entry["superpopulation"] in {args.superpopulation}'
    else:
        q_population = True

    ## get metadata
    if args.no_cache:
        onekg_dict = get_metadata()
    else:
        cachedir = os.path.expanduser('~/.figshare')
        cachefile = os.path.expanduser(f'{cachedir}/onekg_dict.pickle')
        if os.path.isfile(cachefile):
            ## cache exists
            logthis(f'Pulling metadata from {cachefile}', logger)
            with open(cachefile, 'rb') as handle:
                onekg_dict = pickle.load(handle)
        else:
            ## download and cache
            onekg_dict = get_metadata()
            if not os.path.isdir(cachedir):
                os.makedirs(cachedir)
            with open(cachefile, 'wb') as handle:
                pickle.dump(onekg_dict, handle)

    ## query
    keepset = []
    for entry in onekg_dict.values():
        qstring = f'({q_sex}) and ({q_population})'
        qstring = qstring.format(**entry)
        keep = eval(qstring)
        if keep:
            keepset.append(entry)

    if args.number:
        filenames = sorted([entry['sample_id'] for entry in keepset])
        tokeep = filenames[0:args.number]
        keepset = [entry for entry in keepset if entry['sample_id'] in tokeep]

    ## download
    if args.no_download:
        json.dump(keepset, sys.stdout, indent=2)
    else:
        ## download
        for entry in keepset:
            logthis(f'Downloading {entry["sample_id"]}', logger)
            outfile = f'{args.dir}/{entry["filename"]}'
            ## link given by figshare api redirects to s3 get actual location 
            s3_url = requests.head(entry['url']).headers['Location']
            ## download
            download(s3_url, outfile, hash=entry['md5'])
    return 0

if __name__ == '__main__':
    args = get_args()
    main(args)
