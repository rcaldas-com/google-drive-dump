# Google Drive Dump
#### Download your latest modified Google Drive files using the Google Cloud API recreating the directory tree localy.

As Google don't have a sync app for Linux, this Python3 script uses the Google API to get your last modified Drive files since the last execution with automated backup purposes.

### What it does:

- Load the API credentials from a json file (get yours from google cloud);
- Connect to a MongoDB to control execution and enable features (you can write in files for simplicity);
- Search for new modified files since last run;
- Recreate the directory tree of files in local disk;
- Download all listed files, converting Google Documents to MS Office related format;
- Recover the list of remaining files if some file don't get downloaded in last sync (so we can debug fails not treated before).

So for exemple you can put the script in crontab of the backup server and include drive folder in a rsnapshot routine to make like a versioning incremental backup. :)

### To do:

- ! Fix special caracters in folder names too. ! 
- Put more info in database to check through a web monitor.
- Alert fails sending email.
- Tell me you... Any improvements are welcome.
