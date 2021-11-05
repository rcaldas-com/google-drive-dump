# Google Drive Dump
#### Download your latest modified Google Drive files using the Google Cloud API.

As I couldn't find a Google sync app for Linux, I made this Python3 script that uses the Google API to get your last modified Drive files since the last execution with automated backup purposes, recreating the directory tree locally.

---
### What it needs:
- Google API Credentials json file named ```credentials.json``` (get yours from [gcloud](https://console.cloud.google.com/apis/credentials/oauthclient))
- MongoDB connection to control execution and store token, in format ```mongodb://user:pwd@server/database```
- Directory to store the files mounted in ```files``` directory
- Variables in a ```.env``` file like that:
  ```
  MONGO_URI=mongodb://user:pwd@server:port/database
  MAIL_ADMIN=admin@domain.com
  MAIL_SERVER=mail.server.com
  MAIL_USERNAME=user@mail.com
  MAIL_PASSWORD=password
  ```
---
### What it does:
- Search for new modified files since last run;
- Recreate the directory tree of files in "/files" volume;
- Convert Google Documents to MS Office related format;
- Recover the list of remaining files if some file don't get downloaded in last sync (so we can debug fails not treated before).

---
### First run:
In first run google Token must be created and stored in database
- This need to be done interactivelly by running ```docker-compose run --rm python```
  - It will permit you insert the authorization code generated in the link that will appers on screen.
  
You credential's account must have "Drive API" enabled, a message will tell you if API is disabled providing a link to enable.

Another runs can be with just ```docker-compose up```. Stop with ```docker-compose down```

---
### To do:
- Alert fails sending email.
- Make GridFS more efficient, it is creating a new file with each run
- Put more info in database to check through a web monitor.
- Tell me you... Any improvements are welcome.
