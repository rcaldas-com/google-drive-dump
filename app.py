#!/usr/bin/env python3
from __future__ import print_function
from os import getenv, path, mkdir
import io
import sys
import time
import json
import pickle
from datetime import datetime
from pymongo import MongoClient
import gridfs
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from mail import send_mail

MAIL_ADMIN = getenv('MAIL_ADMIN')
API = getenv('API')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
INIT_DATE = datetime.strptime('01082019','%d%m%Y') # Initial date to get from

# MongoDB
db = MongoClient(getenv('MONGO_URI')).get_database()
col = db['drivedump']
doc = col.find_one({})
if not doc:
    col.insert_one(
        {'name': 'drivedump unique document', 'last_sync': INIT_DATE})
    doc = col.find_one({})
fs = gridfs.GridFS(db)

# Get token from GridFS
token = fs.find_one({'app': 'drivedump', 'filename': 'token'})
if token:
    with open('/google.token', 'wb') as tokenfile:
        tokenfile.write(token.read())
else:
    print('Token not found in gridfs.')

# Create google service
creds = None
if path.isfile('/google.token'):
    with open('/google.token', 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credential', SCOPES)
        creds = flow.run_console() # run_local_server(port=4000)
    with open('/google.token', 'wb') as tokenfile:
        pickle.dump(creds, tokenfile)
    with open('/google.token', 'rb') as tokenfile:
        id = fs.put(tokenfile.read(), app='drivedump', filename='token')
drive = build('drive', 'v3', credentials=creds)

# Check pending files
files = doc.get('pending_files')
if files:
    print(f'{len(files)} pending files to download found...')
else:
    print('Searching online for new files...')
    files = []
    page_token = None
    # query = "name contains 'Curso Online Cuidados Paliativos'"
    query = 'modifiedTime > \'%s\'' %doc['last_sync'].strftime('%Y-%m-%dT%H:%M:%S')
    query_time = datetime.utcnow()
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
    file_count = len(files)
    print(f'{file_count} modified files since last sync')
    doc['last_sync'] = query_time
    if file_count == 0:
        col.update_one({}, {'$set': doc})
        exit(0)
    # Fix special caracters in file names (just had issues with the '/' yet)
    for file in files:
        if '/' in file['name']:
            files.remove(file)
            file['name'] = file['name'].replace('/', '-')
            files.append(file)
    
# Clone list to manage download progress
new_files = files.copy()

# Function to get full path of file recursively
def get_parent(dirId, last_dir=''):
    d = drive.files().get(fileId=dirId,
                          fields='id,name,parents').execute()
    if '/' in d['name']:
        print(f'Bad dirname in "{d["name"]}" !')
        d['name'] = d['name'].replace('/', '-')
    if d.get('parents'):
        new_dir = get_parent(d['parents'][0], d['name'])
        result = path.join(new_dir, last_dir)
        if not path.isdir(result): mkdir(result)
        return result
    # No parents, must be in root_dir
    result = path.join('/files', last_dir)
    if not path.isdir(result): mkdir(result)
    return result

def downl_doc(file_id, dst_file, mime_type=None, doc=True):
    if doc:
        # Export google documments
        request = drive.files().export_media(fileId=file_id,
                                            mimeType=mime_type)
    else:
        # Download general files
        request = drive.files().get_media(fileId=file_id)
    fh = io.FileIO(dst_file, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %s: %d%%." %(dst_file,int(status.progress() * 100)))
    new_files.remove(f)

# Download files
for f in files:
    try:
        if doc.get('excludes'):
            if f['id'] in doc['excludes']:
                new_files.remove(f)
                continue
        if f.get('parents'):
            right_dir = get_parent(f['parents'][0])
        else:
            right_dir = '/files'
        if f['mimeType'] == 'application/vnd.google-apps.document':
            downl_doc(f['id'],
                        path.join(right_dir, f['name']+'.docx'),
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        elif f['mimeType'] == 'application/vnd.google-apps.spreadsheet':
            downl_doc(f['id'],
                    path.join(right_dir, f['name']+'.xlsx'),
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        elif f['mimeType'] == 'application/vnd.google-apps.drawing':
            downl_doc(f['id'],
                    path.join(right_dir, f['name']+'.svg'),
                    'image/svg+xml')
        elif f['mimeType'] == 'application/vnd.google-apps.presentation':
            downl_doc(f['id'],
                    path.join(right_dir, f['name']+'.pptx'),
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation')
        elif f['mimeType'] == 'application/vnd.google-apps.form':
            print(f"\nFile '{path.join(right_dir, f['name'])}' is a Form")
            new_files.remove(f)
        # Just a folder, throw it:
        elif f['mimeType'] == 'application/vnd.google-apps.folder':
            new_files.remove(f)
            continue
        # Not a Google Document, so download normaly:
        else:
            downl_doc(f['id'], path.join(right_dir, f['name']), doc=False)
    except Exception as e:
        exclude_link = f"{API}?exclude={f['id']}"
        if 'too large' in str(e):
            msg = f"The file {path.join(right_dir, f['name'])} is too large to be exported by GDrive API.\nUse this link to exclude the file from drivedump:\n{exclude_link}\n\nSystem Error Message: \n{str(e)}"
            print(msg)
            send_mail(MAIL_ADMIN, 'Drive - Arquivo muito grande', msg)
        elif 'Rate Limit Exceeded' in str(e):
            msg = f"Rate limit exceeded\n\nSystem Error Message: \n{str(e)}"
            print(msg)
            doc['pending_files'] = new_files
            col.update_one({}, {'$set': doc})
            send_mail(MAIL_ADMIN, 'Drive - Rate limit exceeded', msg)
            exit(0)
        else:
            msg = f"Error to download file {path.join(right_dir, f['name'])}\nUse this link to exclude the file from drivedump:\n{exclude_link}\n\nSystem Error Message: \n{str(e)}"
            print(msg)
            send_mail(MAIL_ADMIN, 'Drive - Falha ao baixar arquivo', msg)

if len(new_files) == 0:
    print(f'All {file_count} files Downloaded.')
    send_mail(MAIL_ADMIN, f'Drive - All {file_count} files downloaded', 'Ok')
else:
    print(f'Remaining {len(new_files)} files to download')
    send_mail(MAIL_ADMIN, f'Drive - Remaining {len(new_files)} files to download', f'Remaining {len(new_files)} files to download')
doc['pending_files'] = new_files
col.update_one({}, {'$set': doc})
