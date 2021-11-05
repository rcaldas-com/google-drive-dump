# Google Drive Dump
#### Download your latest modified Google Drive files using the Google Cloud API.

As I couldn't find a Google sync app for Linux, I made this Python3 script that uses the Google API to get your last modified Drive files since the last execution with automated backup purposes, recreating the directory tree locally.

### What it needs:
- Google API Credentials json file mounted in ```/credentials.json``` (get yours from [gcloud](https://console.cloud.google.com/iam-admin/serviceaccounts))
- MongoDB URI to control execution and store token, in format ```mongodb://user:pwd@server/database```
- Directory to store the files mouinted in ```/files```

"Set each one in docker-compose file"

### What it does:
- Search for new modified files since last run;
- Recreate the directory tree of files in "/files" volume;
- Convert Google Documents to MS Office related format;
- Recover the list of remaining files if some file don't get downloaded in last sync (so we can debug fails not treated before).

### To do:
- Alert fails sending email.
- Make GridFS more efficient, it is creating a new file with each run
- Put more info in database to check through a web monitor.
- Tell me you... Any improvements are welcome.
