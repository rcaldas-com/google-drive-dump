# Google Drive Dump
#### Download your latest modified Google Drive files using the Google Cloud API.

As Google don't have a sync app for Linux, this Python3 script uses the Google API to get your last modified Drive files since the last execution with automated backup purposes, recreating the directory tree localy.

### What it needs:
- Google API Credentials json file (get yours from gcloud)
- MongoDB connection URI to control execution and store token
- Dir to store the files
(Set each one in docker-compose file)

### What it does:
- Search for new modified files since last run;
- Recreate the directory tree of files in "/files" volume;
- Convert Google Documents to MS Office related format;
- Recover the list of remaining files if some file don't get downloaded in last sync (so we can debug fails not treated before).

### To do:
- Alert fails sending email.
- Put more info in database to check through a web monitor.
- Tell me you... Any improvements are welcome.
