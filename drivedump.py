#!/usr/bin/env python3
from __future__ import print_function
import os
import io
import sys
sys.path.append('/usr/local/lib/python3.7/site-packages') # to run in cron
import time
import json
import pickle
import os.path
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build
from pymongo import MongoClient, ASCENDING, errors
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow

### Install python modules
# pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

### Get base dir and load .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

### Root path for drive files
drive_dir = '/var/drive'
if not os.path.isdir(drive_dir): os.mkdir(drive_dir)

### Mongodb connection and initialize
MONGO_URI = os.environ.get('MONGO_URI')
MONGODB_CONNECT = False

mongo = MongoClient(MONGO_URI)
db = mongo['inpa']
control = db['drive_ctrl']
# control.create_index([('id', ASCENDING)], unique=True)
# control.insert_one({'id': 'last_sync',
#                     'value': datetime.strptime('01082019','%d%m%Y')}) # Initial date to get from

### Google API credentials
CREDENTIALS = os.environ.get('CREDENTIALS')
GTOKEN = os.environ.get('GTOKEN')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
### Create the google service
creds = None
if os.path.exists(GTOKEN):
    with open(GTOKEN, 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS, SCOPES)
        creds = flow.run_local_server(port=4000)
    with open(GTOKEN, 'wb') as token:
        pickle.dump(creds, token)
drive = build('drive', 'v3', credentials=creds)

### Check if have a pending update:
if control.find_one({'id': 'pending_files'}):
    print('Pending files to download found.')
    files = control.find_one({'id': 'pending_files'}).get('files')
else:
    print('Searching online for new files...')

    ### Get datetime of last sync to search files by modTime
    last_sync = control.find_one({'id': 'last_sync'}).get('value')

    ### Save now datetime to next run
    query_time = datetime.utcnow()

    ### Get Files by modtime
    files = []
    page_token = None
    query = 'modifiedTime > \'%s\'' %last_sync.strftime('%Y-%m-%dT%H:%M:%S')
    while True:
        response = drive.files().list(q=query,
                                      pageSize=50,
                                      spaces='drive',
                                      fields='nextPageToken,files(id, name, parents, mimeType, modifiedTime, createdTime)',
                                      pageToken=page_token).execute()
        for file in response.get('files', []):
            files.append(file)
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break

    print(f'{len(files)} modified files since last sync')
    if len(files) == 0:
        control.update_one({'id': 'last_sync'},
                           {'$set': {'value': query_time}})
        exit(0)

    ### Fix special caracters in file names (just had issues with the '/' so far)
    for file in files:
        if '/' in file['name']:
            print(file)
            files.remove(file)
            new_name = file['name'].replace('/', '-')
            file['name'] = new_name
            files.append(file)

    ### Save new list in db as pending
    control.insert_one({'id': 'pending_files',
                        'files': files,
                        'last_sync': last_sync,
                        'query_time': query_time})

### Clone list to control download file progress removing from new list:
new_files = files.copy()

### Function to get full path of file recursively
def get_parent(dirId, last_dir=''):
    d = drive.files().get(fileId=dirId,
                          fields='id,name,parents').execute()
    if d.get('parents'):
        new_dir = get_parent(d['parents'][0], d['name'])
        result = os.path.join(new_dir, last_dir)
        if not os.path.isdir(result): os.mkdir(result)
        return result
    ### No parents, must be in root_dir
    result = os.path.join(drive_dir, last_dir)
    if not os.path.isdir(result): os.mkdir(result)
    return result

### Function to export google documments
def downl_doc(file_id, dst_file, mime_type):
        request = drive.files().export_media(fileId=file_id,
                                             mimeType=mime_type)
        fh = io.FileIO(dst_file, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %s: %d%%." %(dst_file,int(status.progress() * 100)))
        new_files.remove(f)

### Download files
for f in files:
    if f.get('parents'):
        right_dir = get_parent(f['parents'][0])
    else:
        right_dir = drive_dir

    try:
        if f['mimeType'] == 'application/vnd.google-apps.document':
            downl_doc(f['id'],
                         os.path.join(right_dir, f['name']+'.docx'),
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

        elif f['mimeType'] == 'application/vnd.google-apps.spreadsheet':
            downl_doc(f['id'],
                      os.path.join(right_dir, f['name']+'.xlsx'),
                      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        elif f['mimeType'] == 'application/vnd.google-apps.drawing':
            downl_doc(f['id'],
                      os.path.join(right_dir, f['name']+'.svg'),
                      'image/svg+xml')

        elif f['mimeType'] == 'application/vnd.google-apps.presentation':
            downl_doc(f['id'],
                      os.path.join(right_dir, f['name']+'.pptx'),
                      'application/vnd.openxmlformats-officedocument.presentationml.presentation')
        ### Just a folder, throw it:
        elif f['mimeType'] == 'application/vnd.google-apps.folder':
            new_files.remove(f)
            continue
        ### Not a Google Document, so download normaly:
        else:
            dst_file = os.path.join(right_dir, f['name'])
            request = drive.files().get_media(fileId=f['id'])
            fh = io.FileIO(dst_file, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print("Download %s: %d%%." %(dst_file,int(status.progress() * 100)))
            new_files.remove(f)
    except Exception as e:
        if 'too large' in str(e):
            print(f"The file '{os.path.join(right_dir, f['name'])}' \
is too large to be exported by GDrive API!\n\
Make a manual backup or reduce file size.\n\nSystem Error Message: \n{str(e)}",
                                                                file=sys.stderr)
            new_files.remove(f)
        else:
            print(e, file=sys.stderr)

if len(new_files) == 0:
    print('Ok!')
    ### Update last sync value:
    query_time = control.find_one({'id': 'pending_files'}).get('query_time')
    control.update_one({'id': 'last_sync'},
                       {'$set': {'value': query_time}})
    ### Delete pending files document:
    control.delete_one({'id': 'pending_files'})
else:
    print(f'Remaining {len(new_files)} files to download')
    control.update_one({'id': 'pending_files'},
                       {'$set': {'files': new_files }})
